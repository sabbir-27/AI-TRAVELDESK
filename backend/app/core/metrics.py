"""Lightweight dependency-free Prometheus text exposition metrics registry."""

from collections import defaultdict
from threading import Lock

_LATENCY_BUCKETS = (0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)


class MetricsRegistry:
    """Thread-safe in-process Prometheus metrics collector."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._http_requests: dict[tuple[str, str, str], int] = defaultdict(int)
        self._http_latency_sum: dict[tuple[str, str], float] = defaultdict(float)
        self._http_latency_count: dict[tuple[str, str], int] = defaultdict(int)
        self._http_latency_buckets: dict[tuple[str, str, float], int] = defaultdict(int)
        self._domain_events: dict[str, int] = defaultdict(int)

    def observe_http_request(
        self,
        *,
        method: str,
        path: str,
        status_code: int,
        duration_seconds: float,
    ) -> None:
        """Record an HTTP request count and latency histogram observation."""
        with self._lock:
            self._http_requests[(method, path, str(status_code))] += 1
            self._http_latency_sum[(method, path)] += duration_seconds
            self._http_latency_count[(method, path)] += 1
            for bound in _LATENCY_BUCKETS:
                if duration_seconds <= bound:
                    self._http_latency_buckets[(method, path, bound)] += 1

    def increment_event(self, event_name: str, amount: int = 1) -> None:
        """Increment a business domain counter (bookings, tickets, errors, etc.)."""
        with self._lock:
            self._domain_events[event_name] += amount

    def render_prometheus(self) -> str:
        """Render all collected metrics in Prometheus text exposition format 0.0.4."""
        lines: list[str] = [
            "# HELP http_requests_total Total HTTP requests processed by FastAPI.",
            "# TYPE http_requests_total counter",
        ]
        with self._lock:
            for (method, path, status_code), count in sorted(self._http_requests.items()):
                labels = f'method="{method}",path="{path}",status="{status_code}"'
                lines.append(f"http_requests_total{{{labels}}} {count}")

            lines.extend(
                [
                    "# HELP http_request_duration_seconds HTTP request latency in seconds.",
                    "# TYPE http_request_duration_seconds histogram",
                ]
            )
            for (method, path), total_count in sorted(self._http_latency_count.items()):
                base_labels = f'method="{method}",path="{path}"'
                for bound in _LATENCY_BUCKETS:
                    bucket_val = self._http_latency_buckets.get((method, path, bound), 0)
                    lines.append(
                        "http_request_duration_seconds_bucket"
                        f'{{{base_labels},le="{bound}"}} {bucket_val}'
                    )
                lines.append(
                    "http_request_duration_seconds_bucket"
                    f'{{{base_labels},le="+Inf"}} {total_count}'
                )
                total_sum = self._http_latency_sum.get((method, path), 0.0)
                lines.append(
                    f"http_request_duration_seconds_sum{{{base_labels}}} {total_sum:.6f}"
                )
                lines.append(
                    f"http_request_duration_seconds_count{{{base_labels}}} {total_count}"
                )

            if self._domain_events:
                lines.extend(
                    [
                        "# HELP traveldesk_domain_events_total Domain events emitted by services.",
                        "# TYPE traveldesk_domain_events_total counter",
                    ]
                )
                for event_name, value in sorted(self._domain_events.items()):
                    lines.append(
                        f'traveldesk_domain_events_total{{event="{event_name}"}} {value}'
                    )

        return "\n".join(lines) + "\n"


metrics_registry = MetricsRegistry()
