# Grafana Workstream

This directory is the shared workspace for Prometheus and Grafana monitoring.

## Scope

- System-level monitoring
- Container-level visibility
- Dashboard provisioning for the chat-web project
- Backend request and WebSocket metrics for pressure testing
- Kafka producer, consumer, lag, and backlog metrics
- PostgreSQL pressure indicators for pressure tests and Kafka load runs

## Quick start

1. Copy `grafana/.env.example` to `grafana/.env`
2. Review `BACKEND_METRICS_TARGET`
3. Start the base app stack from the repo root first so the shared Docker network `chat-web_default` exists
4. Start the monitoring stack with:
   `docker compose -f grafana/docker-compose.yml --env-file grafana/.env up -d`

## What is included

- `docker-compose.yml`
  Prometheus, Grafana, PostgreSQL Exporter, Node Exporter, and cAdvisor
- `prometheus/prometheus.yml`
  Initial scrape targets
- `provisioning/`
  Auto-loaded datasource and dashboard providers
- `dashboards/system-overview.json`
  Minimal dashboard for backend, WebSocket, container signals, and key PostgreSQL pressure indicators
- `dashboards/kafka-observability.json`
  Kafka producer, consumer, lag, backlog, and correlated PostgreSQL pressure dashboard

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
5. Confirm `prometheus`, `chat-backend`, `postgres-exporter`, `node-exporter`, and `cadvisor` are `UP`
6. Open Grafana:
   `http://localhost:3003`
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
   - `Postgres Scrape Status`
   - `Postgres Transactions Per Second`
   - `Postgres Rows Changed Per Second`
   - `Postgres Sessions by State`
   - `Container CPU Rate`
   - `Container Memory Working Set`

## Kafka Monitoring Flow

1. Start the base app stack so the shared Docker network `chat-web_default` exists:
   `docker compose up --build -d`
2. Copy Kafka env file:
   `copy kafka\.env.example kafka\.env`
3. Start Kafka and exporter:
   `docker compose -f kafka/docker-compose.yml --env-file kafka/.env up -d kafka kafka-ui kafka-exporter`
4. Start the optional slow mock consumer when you want lag to accumulate:
   `docker compose -f kafka/docker-compose.yml --env-file kafka/.env --profile consumer-demo up -d mock-slow-consumer`
5. Start the monitoring stack:
   `docker compose -f grafana/docker-compose.yml --env-file grafana/.env up -d`
6. Confirm Prometheus targets are `UP` at `http://localhost:9090/targets`
   - `chat-backend`
   - `kafka-exporter`
   - `postgres-exporter`
7. Open Grafana and load `Kafka Producer Consumer Lag`
8. Run the Kafka load test:
   `python kafka/scripts/run_kafka_load_test.py --profile kafka/load-profile.example.json`
9. Watch these panels:
   - `Producer Rate`
   - `Consumer Rate`
   - `Consumer Lag`
   - `Backlog`
   - `Produced vs Consumed Offsets`
   - `Postgres Scrape Status`
   - `Postgres Transactions Per Second`
   - `Postgres Rows Changed Per Second`
   - `Postgres Sessions by State`

## Route-level interpretation

- `HTTP Throughput by Route` now groups dynamic routes by FastAPI route template, such as `/chatrooms/{room_id}/messages`
- `HTTP Throughput by Route` excludes `OPTIONS` so business API traffic is easier to read
- `HTTP Preflight Requests` is the companion panel for browser CORS preflight traffic
- `Backend Request Rate` still reflects the overall backend HTTP request volume, so it can rise from both business requests and preflight requests

## Notes for Docker Desktop on Windows

- `node-exporter` and `cadvisor` can be more environment-sensitive than backend metrics.
- If container-level panels are blank but `chat-backend` is `UP`, the minimal monitoring stack is still usable for backend pressure testing.
- If you rename the backend container or Compose project, update `BACKEND_METRICS_TARGET` in `grafana/.env`.

## Suggested next steps for the owner

- Add application-level counters around chat send, fetch, and persistence flows
- Split dashboards into system, Kafka, and application views when metrics mature
