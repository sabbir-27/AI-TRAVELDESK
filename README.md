# AI TravelDesk

**Enterprise AI-Powered Multi-Tenant B2B Travel Agency Operating Platform**

AI TravelDesk empowers independent travel agencies with centralized LangGraph multi-agent flight automation, pluggable GDS/NDC flight supplier adapters, white-label website chat widgets & REST APIs, multi-gateway payment processing + e-ticket issuance, and a collaborative human agent support workspace — all secured by strict tenant isolation and PostgreSQL Row-Level Security (RLS).

## Platform Capabilities

- **Multi-Tenant SaaS Core & RBAC**: `SUPER_ADMIN`, `AGENCY_OWNER`, `AGENCY_MANAGER`, `TRAVEL_AGENT`, and `CUSTOMER` roles with verified JWT + agency membership claims and PostgreSQL RLS across tenant tables.
- **LangGraph AI Multi-Agent Orchestration**: Supervisor router coordinating 14 specialized nodes (multilingual English/Bangla/Banglish intent detection, slot-filling, supplier flight search, fare rules, anti-hallucination safety guard, booking, ticketing, modification, cancellation, refund, and human handoff).
- **Adapter-Based Flight & Payment Integrations**: Unified supplier interface (`Sandbox`, `Amadeus`, `Duffel`) and payment gateways (`SSLCommerz`, `bKash`, `Nagad`, `Stripe`, `Sandbox`) with signed webhook verification.
- **Website Integration & White-Label Widget**: Embeddable `/widget.js` chat bundle with domain-origin & scoped token enforcement, plus hashed `X-API-Key` REST integration.
- **Human Support Workspace**: Live polling agent inbox, staff assignment, AI-to-human takeover / release / resolve, click-to-fill AI reply suggestions, internal staff notes, and support ticket management.
- **Production Operations**: Prometheus `/metrics`, Grafana dashboard provisioning, Nginx reverse proxy, multi-stage production Dockerfiles, AWS ECS/Terraform IaC, and GitHub Actions CI/CD.

## Documentation

- [System Architecture](docs/architecture.md)
- [Database Schema & ERD](docs/database-schema.md)
- [Security Architecture](docs/security.md)
- [Implementation Plan & Risks](docs/implementation-plan.md)
- [API Documentation](docs/api-documentation.md)
- [Website & API Integration Guide](docs/integration-guide.md)
- [Deployment & Operations Guide](docs/deployment-guide.md)

## Quick Start (Local Development)

```bash
cp .env.example .env
docker compose up --build
```

Services:
- Frontend UI: `http://localhost:3000`
- Backend API & OpenAPI Docs: `http://localhost:8000/docs`
- Embeddable Widget Script: `http://localhost:8000/widget.js`
- Prometheus Metrics: `http://localhost:8000/metrics`

## Running Verification Locally

### Backend (Python 3.12)
```bash
cd backend
.venv/bin/ruff check app tests
.venv/bin/pytest -v
```

### Frontend (Next.js 15 + TypeScript)
```bash
cd frontend
npm run typecheck
npm run test
npm run build
```
