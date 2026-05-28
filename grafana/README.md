# Grafana Workstream

This directory is the shared workspace for Prometheus and Grafana monitoring.

## Scope

- System-level monitoring
- Container-level visibility
- Dashboard provisioning for the chat-web project
- Backend request and WebSocket metrics for pressure testing

## Quick start

1. Copy `grafana/.env.example` to `grafana/.env`
2. Review `BACKEND_METRICS_TARGET`
3. Start the base app stack from the repo root first so the shared Docker network `chat-web_default` exists
4. Start the monitoring stack with:
   `docker compose -f grafana/docker-compose.yml --env-file grafana/.env up -d`

## What is included

- `docker-compose.yml`
  Prometheus, Grafana, Node Exporter, and cAdvisor
- `prometheus/prometheus.yml`
  Initial scrape targets
- `provisioning/`
  Auto-loaded datasource and dashboard providers
- `dashboards/system-overview.json`
  Minimal dashboard for backend, WebSocket, and container signals

## Recommended startup order

1. Start `chat-web` first from the repository root
2. Confirm the backend is healthy at `http://localhost:8000/health`
3. Start Grafana/Prometheus from `grafana/`

This order is recommended because Prometheus scrapes the backend over the shared Docker network as `chat_backend:8000`.
That network is created when the base `chat-web` stack starts.

## Minimal pressure-test validation flow

1. Start the base app stack:
   `docker compose up --build -d`
2. Confirm the backend metrics endpoint is live:
   `http://localhost:8000/metrics`
3. Start the monitoring stack:
   `docker compose -f grafana/docker-compose.yml --env-file grafana/.env up -d`
4. Open Prometheus:
   `http://localhost:9090/targets`
5. Confirm `prometheus`, `chat-backend`, `node-exporter`, and `cadvisor` are `UP`
6. Open Grafana:
   `http://localhost:3001`
7. Sign in with the values from `grafana/.env`
8. Open the `Chat Web Minimal Observability` dashboard
9. Generate activity:
   - browse the frontend
   - call `http://localhost:8000/health`
   - run backend pressure tests
10. Confirm these panels move during load:
   - `Backend Request Rate`
   - `Backend p95 Latency`
   - `Active WebSocket Connections`
   - `Container CPU Rate`
   - `Container Memory Working Set`

## Notes for Docker Desktop on Windows

- `node-exporter` and `cadvisor` can be more environment-sensitive than backend metrics.
- If container-level panels are blank but `chat-backend` is `UP`, the minimal monitoring stack is still usable for backend pressure testing.
- If you rename the backend container or Compose project, update `BACKEND_METRICS_TARGET` in `grafana/.env`.

## Suggested next steps for the owner

- Extend metrics for Kafka producer/consumer throughput and lag
- Add application-level counters around chat send, fetch, and persistence flows
- Split dashboards into system, Kafka, and application views when metrics mature
