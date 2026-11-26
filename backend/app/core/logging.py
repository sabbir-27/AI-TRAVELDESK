"""Structured logging configuration with PII redaction using structlog."""

import logging
import sys
from typing import Any

import structlog

_SENSITIVE_KEY_MARKERS = (
    "password",
    "passwd",
    "secret",
    "token",
    "authorization",
    "api_key",
    "passport",
    "cvv",
    "card_number",
    "credit_card",
    "ssn",
)


def _scrub_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            k: "[REDACTED]"
            if any(marker in str(k).lower() for marker in _SENSITIVE_KEY_MARKERS)
            else _scrub_value(v)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [_scrub_value(item) for item in value]
    return value


def redact_pii_processor(
    _: Any,
    __: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Redact credentials, tokens, and sensitive PII fields before serialization."""
    for key in list(event_dict.keys()):
        if any(marker in key.lower() for marker in _SENSITIVE_KEY_MARKERS):
            event_dict[key] = "[REDACTED]"
        else:
            event_dict[key] = _scrub_value(event_dict[key])
    return event_dict


def configure_logging(debug: bool = False) -> None:
    """Configure stdlib and structlog JSON/console logging."""
    log_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        redact_pii_processor,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if debug:
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a bound structured logger."""
    return structlog.get_logger(name)
