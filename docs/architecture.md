# AI TravelDesk — System Architecture

## 1. Overview

**AI TravelDesk** is an enterprise-grade, multi-tenant B2B SaaS + AI Multi-Agent operating platform for travel agencies. The platform owner provides centralized AI flight-consultant infrastructure, supplier-agnostic flight booking workflows, payment orchestration, and white-label distribution channels (JavaScript Chatbot Widget, versioned REST API, and White-Label Booking Interface) to independent travel agencies.

```
Platform Owner (Super Admin)
    │
    ▼
AI TravelDesk SaaS Platform (Next.js + FastAPI + LangGraph + PostgreSQL/RLS + Redis)
    │
    ├──► AI Multi-Agent Supervisor (LangGraph)
    │       └── Intent, Planning, Search, Comparison, Fare Rules, Passenger, Booking,
    │           Payment, Ticketing, Modification, Cancellation, Refund, Support, Handoff
    │
    └──► Travel Agency Tenants (Agency A, B, C, ...)
            ├── JavaScript Chatbot Widget (<script data-agency-id="...">)
            ├── Versioned REST API (/api/v1/...)
            └── White-Label Booking Portal & Human Agent Workspace
                    │
                    ▼
                End Customers
```

## 2. Core Architectural Principles

1. **Strict Multi-Tenant Isolation**:
   - Shared PostgreSQL database with mandatory `agency_id` tenant foreign keys on all tenant-scoped tables.
   - PostgreSQL Row-Level Security (RLS) policies enforced via session-scoped settings (`app.current_agency_id`, `app.is_super_admin`).
   - Tenant identity is **never** trusted from raw browser query params or request bodies; it is resolved exclusively from verified JWT claims, scoped public widget tokens, or hashed agency API credentials.
2. **API-First & Decoupled Frontend/Backend**:
   - Backend: Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2 (async), Alembic, Redis, Celery.
   - Frontend: Next.js App Router, React, TypeScript (strict), Tailwind CSS, TanStack Query, React Hook Form + Zod.
3. **Adapter-Based External Integrations**:
   - Flight suppliers (`Amadeus`, `Duffel`, `Sabre`, `Travelport`) sit behind a unified `FlightSupplierAdapter` interface.
   - Payment gateways (`SSLCommerz`, `bKash`, `Nagad`, `Stripe`) sit behind a unified `PaymentGatewayAdapter` interface with server-side verification and signed webhooks.
4. **Deterministic Transactional Safety for AI**:
   - LangGraph Supervisor orchestrates specialized agents using validated backend tools and structured outputs.
   - State-machine-driven booking lifecycle (`REQUESTED` -> `FLIGHT_SEARCHED` -> ... -> `COMPLETED`) with idempotency keys and immutable audit logs.
   - The AI never fabricates flights, prices, PNRs, payment confirmations, or e-tickets.

## 3. Monorepo Structure

```text
ai-traveldesk/
├── frontend/               # Next.js App Router application (TypeScript + Tailwind)
├── backend/                # FastAPI application, SQLAlchemy models, Alembic, LangGraph, Celery
│   ├── app/
│   │   ├── api/            # Versioned REST endpoints (/api/v1/...)
│   │   ├── core/           # Settings, security, logging, DB & Redis clients
│   │   ├── models/         # SQLAlchemy 2 normalized multi-tenant ORM models
│   │   ├── schemas/        # Pydantic v2 request/response contracts
│   │   ├── repositories/   # Tenant-aware data access layer
│   │   ├── services/       # Business logic & state machine workflows
│   │   ├── integrations/   # Flight supplier & payment gateway adapters
│   │   ├── agents/         # LangGraph supervisor & specialized sub-agents
│   │   ├── workflows/      # Booking lifecycle & recovery orchestrators
│   │   ├── middleware/     # Tenant context, rate limiting, audit, security headers
│   │   ├── tasks/          # Celery async jobs (ticketing, notifications, billing)
│   │   └── main.py
│   ├── migrations/         # Alembic schema migrations
│   └── tests/              # Unit, API, auth, tenant isolation, and workflow tests
├── widget/                 # Embeddable white-label JS chatbot widget
├── infrastructure/         # Dockerfiles, AWS IaC/templates, Prometheus/Grafana configs
├── docs/                   # Architecture, DB schema, API, security, deployment guides
├── docker-compose.yml
└── .env.example
```

## 4. Phase 1 Foundation Architecture

In Phase 1, the following core building blocks are established:

- **Authentication & RBAC Core**:
  - Argon2id/bcrypt password hashing via `pwdlib` / `passlib`.
  - Short-lived JWT access tokens + rotating opaque/JWT refresh tokens (stored as SHA-256 hashes with reuse detection and revocation).
  - Roles: `SUPER_ADMIN`, `AGENCY_OWNER`, `AGENCY_MANAGER`, `TRAVEL_AGENT`, `CUSTOMER`.
- **Database & Multi-Tenancy Foundation**:
  - Complete normalized schema (28 core tables) with UUID primary keys, `created_at` / `updated_at` timestamps, soft-delete (`deleted_at`) where appropriate, and RLS policy scaffolding.
- **Infrastructure**:
  - Docker Compose stack (`postgres:16`, `redis:7`, `backend`, `frontend`) with health checks.
- **Frontend Foundation**:
  - Next.js App Router shell, design tokens (Stripe/Linear/Vercel-inspired light/dark theme), centralized API client with automatic refresh-token retry, React Query, and `/login`, `/register`, `/dashboard` protected route flow.
