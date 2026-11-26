# AI TravelDesk — Deployment & Operations Guide

## 1. Local Development with Docker Compose

1. Copy `.env.example` to `.env` and adjust local secrets:
   ```bash
   cp .env.example .env
   ```
2. Start PostgreSQL, Redis, FastAPI Backend, and Next.js Frontend:
   ```bash
   docker compose up --build
   ```
3. Run database migrations (automatically executed by container entrypoint or manually):
   ```bash
   docker compose exec backend alembic upgrade head
   ```
4. Access local services:
   - Frontend: `http://localhost:3000`
   - Backend API / OpenAPI docs: `http://localhost:8000/docs`
   - Widget bundle: `http://localhost:8000/widget.js`
   - Prometheus metrics: `http://localhost:8000/metrics`
   - PostgreSQL: `localhost:5432` | Redis: `localhost:6379`

---

## 2. Production Docker Compose Stack (`docker-compose.prod.yml`)

`docker-compose.prod.yml` runs multi-stage hardened production images behind Nginx alongside Prometheus and Grafana:

- Multi-stage images:
  - [`infrastructure/docker/backend.prod.Dockerfile`](../infrastructure/docker/backend.prod.Dockerfile) (non-root `app` user, 4 Uvicorn workers, `/health` probe)
  - [`infrastructure/docker/frontend.prod.Dockerfile`](../infrastructure/docker/frontend.prod.Dockerfile) (Next.js standalone output, non-root `nextjs` user)
- Reverse proxy: [`infrastructure/nginx/nginx.conf`](../infrastructure/nginx/nginx.conf) (routes `/api/`, `/widget.js`, `/health`, `/`, and restricts `/metrics` to private RFC1918 networks)
- Start with strong production secrets set in the environment:
  ```bash
  export POSTGRES_PASSWORD="<strong-db-password>"
  export JWT_SECRET_KEY="<64-char-random-secret>"
  export ENCRYPTION_KEY="<fernet-key>"
  export GRAFANA_ADMIN_PASSWORD="<strong-grafana-password>"
  docker compose -f docker-compose.prod.yml up -d --build
  ```

Note: When `APP_ENV=production`, `Settings.validate_production_security()` enforces `DEBUG=false`, rotated `JWT_SECRET_KEY` and `ENCRYPTION_KEY`, and disallows `*` in `CORS_ORIGINS` (disabling `/docs`, `/redoc`, and `/openapi.json` automatically).

---

## 3. Monitoring & Alerting (`infrastructure/monitoring/`)

- **Scrape configuration**: [`infrastructure/monitoring/prometheus.yml`](../infrastructure/monitoring/prometheus.yml) scrapes `backend:8000/metrics` every 15s.
- **Alert rules**: [`infrastructure/monitoring/alerts.yml`](../infrastructure/monitoring/alerts.yml) triggers `BackendHighErrorRate` (>5% 5xx for 5m) and `BackendHighLatencyP95` (>1.5s P95 latency for 5m).
- **Grafana provisioning**: Auto-provisioned datasource and [`ai-traveldesk-overview.json`](../infrastructure/monitoring/grafana/dashboards/ai-traveldesk-overview.json) dashboard exposed on port `3001` in `docker-compose.prod.yml`.

---

## 4. AWS ECS Fargate + RDS + ElastiCache + CI/CD

- **Infrastructure as Code (Terraform)**: [`infrastructure/aws/terraform/main.tf`](../infrastructure/aws/terraform/main.tf) defines ECS Cluster (with Container Insights), immutable ECR repositories with push vulnerability scanning, encrypted Multi-AZ PostgreSQL 16 RDS (`deletion_protection = true`), ElastiCache Redis 7, and 30-day CloudWatch log groups.
- **ECS Task Definitions**: [`ecs-task-definition-backend.json`](../infrastructure/aws/ecs-task-definition-backend.json) & [`ecs-task-definition-frontend.json`](../infrastructure/aws/ecs-task-definition-frontend.json) wire AWS Secrets Manager ARNs and container health checks.
- **CI Pipeline** ([`.github/workflows/ci.yml`](../.github/workflows/ci.yml)): Runs `ruff check`, `pytest -v`, `tsc --noEmit`, `vitest run`, `next build`, and `docker compose config` validation on PRs and pushes.
- **CD Pipeline** ([`.github/workflows/cd.yml`](../.github/workflows/cd.yml)): Uses GitHub OIDC -> AWS IAM Role to build & push immutable tags to ECR and force rolling ECS Fargate deployments (gated by `vars.AWS_DEPLOY_ENABLED == 'true'`).
