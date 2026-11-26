# AI TravelDesk — API Documentation

All API endpoints are versioned under `/api/v1` and documented interactively via OpenAPI (`/api/v1/openapi.json`, `/docs`, `/redoc` in non-production environments).

## Phase 1 & Phase 2 Endpoints (Implemented)

### Health
- `GET /health` — Basic liveness probe.
- `GET /api/v1/health` — Readiness probe checking PostgreSQL and Redis connectivity.

### Authentication & Session
- `POST /api/v1/auth/register` — Register a new customer user account. Returns user profile and token pair.
- `POST /api/v1/auth/login` — Authenticate with email and password. Returns JWT access token, rotating refresh token, and user context.
- `POST /api/v1/auth/refresh` — Exchange a valid refresh token for a new access/refresh token pair (with reuse detection).
- `POST /api/v1/auth/logout` — Revoke the current refresh token family.
- `GET /api/v1/auth/me` — Return the authenticated user's profile, RBAC role, and tenant membership.

### Agency Onboarding & Plans (Public)
- `GET /api/v1/agencies/plans` — List active SaaS subscription tiers (`STARTER`, `PROFESSIONAL`, `BUSINESS`, `ENTERPRISE`).
- `POST /api/v1/agencies/register` — Register a new travel agency tenant (`PENDING`), owner account (`AGENCY_OWNER`), default AI config, and initial `TRIALING` subscription.

### Super Admin Control Plane (`SUPER_ADMIN` only)
- `GET /api/v1/admin/dashboard` — Global agency, user, booking, subscription, and MRR metrics.
- `GET /api/v1/admin/agencies` — List/filter agencies by status or search term.
- `GET /api/v1/admin/agencies/{agency_id}` — Inspect agency details, counts, and subscription.
- `POST /api/v1/admin/agencies/{agency_id}/approve` — Approve a pending/suspended agency (`ACTIVE`).
- `POST /api/v1/admin/agencies/{agency_id}/suspend` — Suspend an agency (`SUSPENDED`).
- `GET /api/v1/admin/plans` — List SaaS subscription plans.
- `GET /api/v1/admin/users` — List platform user accounts.
- `GET /api/v1/admin/subscriptions` — List agency subscriptions with plan metadata.
- `GET /api/v1/admin/bookings` — List global bookings across tenants for Super Admin monitoring.
- `GET /api/v1/admin/audit-logs` — List immutable platform audit events.

### Tenant-Scoped Agency Workspace (Verified JWT + `AgencyMember`)
- `GET /api/v1/agency/dashboard` — Agency metrics, status, and subscription usage.
- `PATCH /api/v1/agency/profile` — Update agency profile, branding colors, and service fees (`AGENCY_OWNER`).
- `GET /api/v1/agency/team` — List staff members (`AGENCY_OWNER`, `AGENCY_MANAGER`).
- `POST /api/v1/agency/team` — Add `AGENCY_MANAGER` or `TRAVEL_AGENT` (`AGENCY_OWNER`, active agency).
- `GET /api/v1/agency/subscription` — View current subscription and quota usage.
- `GET /api/v1/agency/invoices` — List agency subscription invoices.
- `POST /api/v1/agency/subscription/change-plan` — Upgrade/downgrade plan tier or billing cycle (`AGENCY_OWNER`, active agency).
- `GET /api/v1/agency/customers`, `POST /api/v1/agency/customers`, `GET /api/v1/agency/customers/{customer_id}` — Tenant-isolated customer records.
- `GET /api/v1/agency/bookings`, `GET /api/v1/agency/bookings/{booking_id}` — Tenant-isolated booking records.
- `GET /api/v1/agency/conversations`, `GET /api/v1/agency/conversations/{conversation_id}` — Tenant-isolated conversation records.
- `GET /api/v1/agency/agent-config`, `PATCH /api/v1/agency/agent-config` — Read and update agency white-label AI persona configuration.
- `GET /api/v1/agency/integrations`, `POST /api/v1/agency/integrations/widget/token`, `PATCH /api/v1/agency/integrations/widget/origins`, `POST /api/v1/agency/integrations/api-keys`, `DELETE /api/v1/agency/integrations/api-keys/{credential_id}` — Widget token, origin allowlist, and REST API key management.

### Public Chatbot Widget (Phase 6, Scoped Widget Token + Origin Auth)
- `GET /widget.js` — Embeddable white-label JavaScript chatbot widget bundle.
- `GET /api/v1/widget/config` — White-label branding and AI persona greeting.
- `POST /api/v1/widget/conversations`, `POST /api/v1/widget/conversations/{conversation_id}/messages`, `GET /api/v1/widget/conversations/{conversation_id}` — Origin-enforced widget chat lifecycle.

### AI Flight Agent (LangGraph Supervisor, Tenant-Isolated)
- `POST /api/v1/agent/conversations` — Create a tenant-scoped AI conversation session with welcome greeting.
- `POST /api/v1/agent/conversations/{conversation_id}/messages` — Send a customer message (English, Bangla, or Banglish) through the LangGraph Supervisor, persist messages & `thread_state`, and return structured agent outputs.
- `GET /api/v1/agent/conversations/{conversation_id}` — Retrieve ordered conversation messages and persisted LangGraph state.

### Flight Suppliers & Bookings (Phase 5, Tenant-Isolated)
- `POST /api/v1/flights/search` — Search flight offers via configured `FlightSupplierAdapter` (`Amadeus`, `Duffel`, or `SandboxFlightAdapter`) and persist offers.
- `POST /api/v1/flights/price` — Revalidate offer availability, fare rules, and price changes.
- `GET /api/v1/flights/offers/{offer_id}` — Retrieve a tenant-scoped persisted offer.
- `POST /api/v1/bookings` — Idempotent reservation creation enforcing offer revalidation, encrypted passenger PII, agency service fee calculation, explicit customer approval, and state-machine progression to `RESERVATION_CREATED`.
- `GET /api/v1/bookings/{booking_id}` — Retrieve tenant-scoped booking details.
- `POST /api/v1/bookings/{booking_id}/verify` — Verify live reservation status against the flight supplier adapter.

## Human Support Workspace (Phase 8, Tenant-Isolated)
- `GET /api/v1/workspace/inbox` — List agency conversations with assignment & preview metadata.
- `GET /api/v1/workspace/conversations/{conversation_id}` — Full conversation thread, customer profile, linked bookings, assignment, and support tickets.
- `POST /api/v1/workspace/conversations/{conversation_id}/assign` — Assign conversation to verified staff in the same agency (`AGENCY_OWNER`, `AGENCY_MANAGER`).
- `POST /api/v1/workspace/conversations/{conversation_id}/takeover` — Human takeover (`HUMAN_ACTIVE`), release to AI (`AI_ACTIVE`), or resolve (`RESOLVED`).
- `POST /api/v1/workspace/conversations/{conversation_id}/reply` — Persist human agent replies and internal notes (`is_internal_note`).
- `GET /api/v1/workspace/conversations/{conversation_id}/suggestions` — Generate AI-assisted reply suggestions from conversation state.
- `GET /api/v1/workspace/support-tickets`, `POST /api/v1/workspace/support-tickets`, `PATCH /api/v1/workspace/support-tickets/{ticket_id}` — Support ticket management.

### Payments, Ticketing, Cancellations, Changes & Refunds (Phase 7)
- `POST /api/v1/payments/initiate` — Initiate an idempotent customer payment session (`sslcommerz`, `bkash`, `nagad`, `stripe`, `sandbox`).
- `POST /api/v1/payments/{payment_id}/verify` — Server-side gateway payment verification.
- `POST /api/v1/payments/webhooks/{gateway}` — HMAC-SHA256 signed gateway webhook callback (`X-Webhook-Signature`).
- `POST /api/v1/bookings/{booking_id}/issue-ticket` — Issue or retry airline e-tickets after confirmed payment (opens urgent recovery `SupportTicket` on `TICKETING_FAILED`).
- `GET /api/v1/bookings/{booking_id}/tickets` — Retrieve issued e-tickets for a booking.
- `POST /api/v1/bookings/{booking_id}/cancel` — Cancel booking with fare-rule penalty calculation (`REFUND_PENDING` if paid).
- `POST /api/v1/bookings/{booking_id}/change` — Modify departure date with penalty and fare difference calculation.
- `POST /api/v1/bookings/{booking_id}/refund` — Process gateway refund and transition booking to `CANCELLED`.
