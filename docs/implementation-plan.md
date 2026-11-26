# AI TravelDesk — Implementation Plan & Risk Register

## 1. Phased Delivery Plan

| Phase | Scope | Exit Criteria |
|-------|-------|---------------|
| **Phase 1: Project Foundation** | Monorepo layout, architecture/DB/security docs, complete SQLAlchemy 2 schema + Alembic migration + RLS policies, FastAPI core + JWT/refresh auth + RBAC, Docker Compose (Postgres, Redis, Backend, Frontend), Next.js App Router + Tailwind + design tokens + Auth UI (`/login`, `/register`, `/dashboard`). | Backend pytest suite (auth, RBAC, token rotation, schema/health) passes; Frontend Vitest + Next.js typecheck/build pass; Docker config validated. |
| **Phase 2: Multi-Tenant SaaS** | Agency registration & Super Admin approval/suspension, tenant isolation tests, RBAC permissions matrix, subscription plans & billing foundation, Super Admin & Agency dashboard shells. | Tenant isolation integration tests prove zero cross-tenant leakage; Super Admin & Agency workflows functional end-to-end. |
| **Phase 3: Frontend Experience** | Complete Public SaaS site (`/`, `/features`, `/solutions`, `/pricing`, `/integrations`, `/about`, `/contact`), full Admin/Agency/Workspace/Customer UIs with charts, tables, light/dark modes. | Component, route-protection, and form tests pass across all portals. |
| **Phase 4: AI Flight Agent** | LangGraph Supervisor + 14 specialized sub-agents, English/Bangla/Banglish intent detection, Postgres checkpointing, tool calling, hallucination guards. | AI evaluation suite (intent, state, handoff, anti-hallucination) passes. |
| **Phase 5: Flight Provider Integration** | Adapter interface + Amadeus/Duffel sandbox adapters, search, offer revalidation/pricing, reservation creation & verification. | Supplier adapter contract tests pass against sandbox mocks/APIs. |
| **Phase 6: Website Integration** | Embeddable JS widget (`widget/`), scoped public tokens, white-label theming, documented agency REST API (`/api/v1/...`). | Widget embeds cleanly on external test HTML page and talks to tenant-scoped API. |
| **Phase 7: Transactions** | SSLCommerz/bKash/Nagad/Stripe adapters, signed webhooks, idempotency, Celery ticketing/recovery workflow, e-tickets, cancellations, modifications, refunds. | State-machine + payment-success/ticketing-failure recovery tests pass. |
| **Phase 8: Human Support** | Real-time workspace inbox, AI response suggestions, human takeover, assignment, internal notes, support tickets. | Multi-agent handoff and human workspace tests pass. |
| **Phase 9: Production Readiness** | Security audit, full E2E tests, Prometheus/Grafana monitoring, AWS deployment configs, GitHub Actions CI/CD, full docs. | CI pipeline green; security & load checks verified. |

## 2. Identified Technical Risks & Mitigations

1. **Cross-Tenant Data Leakage**:
   - *Risk*: Developer forgets `agency_id` filter on a query or trusts a client-supplied header.
   - *Mitigation*: Mandatory `TenantMixin`, repository helpers requiring `TenantContext`, and PostgreSQL Row-Level Security (`FORCE ROW LEVEL SECURITY`) as defense-in-depth.
2. **AI Hallucination of Fares, PNRs, or Tickets**:
   - *Risk*: LLM fabricates flight availability, prices, or confirmation codes.
   - *Mitigation*: Strict tool-call-only data retrieval, Pydantic structured outputs, and backend state machine that only transitions to `RESERVATION_CREATED` / `TICKETED` upon verified supplier adapter responses.
3. **Payment Success + Ticketing Failure Split-Brain**:
   - *Risk*: Customer payment succeeds at gateway (bKash/SSLCommerz/Stripe), but airline GDS ticketing times out or fare expires.
   - *Mitigation*: Explicit `TICKETING_FAILED` state, idempotency keys on every charge/reservation, and automated Celery recovery + human-agent escalation + refund workflow.
4. **Refresh Token Replay / Session Hijacking**:
   - *Risk*: Intercepted refresh tokens reused by attackers.
   - *Mitigation*: One-time refresh token rotation with `family_id` tracking; reuse of a rotated token revokes the entire token family immediately.
5. **External Provider API Rate Limits & Latency**:
   - *Risk*: Slow GDS search responses degrade AI chat UX.
   - *Mitigation*: Redis offer caching with strict TTL + mandatory price revalidation before booking, plus async Celery workers for non-blocking ticketing and notifications.
