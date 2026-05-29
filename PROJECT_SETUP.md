# Chat Web Project Setup Draft

This draft gives each teammate a consistent working area under the same repository.

## Recommended workflow

1. Copy the root environment file:
   `cp .env.example .env`
2. If you are working on Kafka, also copy:
   `cp kafka/.env.example kafka/.env`
3. If you are working on Grafana/monitoring, also copy:
   `cp grafana/.env.example grafana/.env`
4. Keep variable names aligned with the root `.env` unless there is a strong reason to diverge.

## Team ownership

- `kafka/`
  Owner scope: steady-state Kafka throughput test, soak test, and large online-user simulation scaffolding.
- `grafana/`
  Owner scope: Prometheus + Grafana stack, system dashboards, and exporter wiring.

## Current draft assumptions

- Base app stack is started from the repository root with `docker compose up`.
- Kafka runs as its own compose project inside `kafka/`.
- Grafana monitoring runs as its own compose project inside `grafana/`.
- Backend metrics are expected to become available at `BACKEND_METRICS_TARGET`.

## Definition of done for each workstream

### Kafka

- Can produce or proxy a sustained `KAFKA_TARGET_MSG_RATE` workload for `KAFKA_TEST_DURATION_SECONDS`.
- Has a documented plan for topic count, partition count, and consumer strategy.
- Includes a separate scenario for `KAFKA_TARGET_ONLINE_USERS` connected users.

### Grafana

- Prometheus can scrape host/system metrics.
- Grafana auto-loads at least one dashboard.
- Dashboard shows CPU, memory, and container visibility.

## Directory rules

- Put runnable compose files inside each workstream directory.
- Put docs and test profiles close to the feature they belong to.
- Avoid adding ad hoc scripts at repo root when they belong under `kafka/` or `grafana/`.
