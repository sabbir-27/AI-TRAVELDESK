# AI TravelDesk — Security Architecture

## 1. Multi-Tenant Isolation

1. **Zero Trust for Client Tenant IDs**:
   - The backend never trusts `agency_id` headers or body fields supplied by an unauthenticated browser.
   - Authenticated dashboard/API users have their active `agency_id` derived from verified JWT claims and verified against `agency_members`.
   - Public widget requests authenticate using signed/scoped widget tokens bound to an approved `agency_id` and allowed origin domains.
   - Server-to-server REST API integrations authenticate via hashed API keys (`SHA-256` prefix + secret) tied to `agency_integrations`.
2. **PostgreSQL Row-Level Security (RLS)**:
   - Each database session sets transaction-local context variables (`SET LOCAL app.current_agency_id = ...`, `SET LOCAL app.is_super_admin = ...`) before executing tenant-scoped queries.
   - Even if an application query omits a `WHERE agency_id = ...` filter, PostgreSQL RLS prevents cross-tenant reads or writes.

## 2. Authentication & Session Security

- **Password Hashing**: Argon2id (via `pwdlib[argon2]`) with per-user cryptographic salt.
- **Access Tokens**: Short-lived JWT (`HS256` in local dev / `RS256` configurable for production), 15-minute default TTL, containing `sub` (user ID), `role`, `agency_id` (nullable for platform-level or un-onboarded users), `jti`, and `type="access"`.
- **Refresh Token Rotation**:
  - 7-day default TTL, persisted in `refresh_tokens` as a SHA-256 hash alongside `family_id`.
  - Every `/api/v1/auth/refresh` call revokes the presented token and issues a fresh pair.
  - Presenting an already-revoked refresh token triggers **token-family revocation** (detecting theft/replay) and forces re-authentication.
- **RBAC**:
  - Roles: `SUPER_ADMIN`, `AGENCY_OWNER`, `AGENCY_MANAGER`, `TRAVEL_AGENT`, `CUSTOMER`.
  - Route dependencies enforce both role membership and tenant membership.

## 3. Sensitive Data Protection

- **Encryption at Rest**: Passport numbers, supplier API secrets, and payment gateway credentials are encrypted using authenticated symmetric encryption (`Fernet` / AES-128-CBC + HMAC-SHA256) keyed via `ENCRYPTION_KEY` environment variable (KMS-backed in AWS).
- **PCI-DSS Scope Reduction**: Raw credit/debit card numbers and CVVs are **never** accepted, logged, or stored by AI TravelDesk; customer payments use hosted/tokenized sessions (SSLCommerz, bKash, Nagad, Stripe) and signed webhook verification.
- **PII Redaction**: Structured logging (`app/core/logging.py`) scrubs keys matching `password`, `secret`, `token`, `authorization`, `api_key`, `passport`, `cvv`, `card_number`, and `ssn` via `redact_pii_processor` before serialization.

## 4. API & Transport Security

- Strict Pydantic v2 input validation on all request payloads and fail-fast production startup checks in `Settings.validate_production_security()` (rejects default secrets, wildcard CORS, or `DEBUG=true` when `APP_ENV=production`).
- Explicit CORS allowlist configured via `CORS_ORIGINS` (never wildcard `*` with credentials) and OpenAPI `/docs`/`/redoc` disabled when `APP_ENV=production`.
- Security response headers (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy`, plus `Strict-Transport-Security` in staging/production).
- Sliding-window rate limiting on `/api/v1/auth/*`, `/api/v1/widget/*`, and `/api/v1/*` routes returning `429 Too Many Requests` and `X-RateLimit-*` headers when exceeded.
- Immutable `audit_logs` capturing actor, agency, action, IP address, user-agent, and before/after state.
