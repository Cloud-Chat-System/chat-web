# Grafana Workstream

This directory is the shared workspace for Prometheus and Grafana monitoring.

## Scope

- System-level monitoring
- Container-level visibility
- Dashboard provisioning for the chat-web project

## Quick start

1. Copy `grafana/.env.example` to `grafana/.env`
2. Review `BACKEND_METRICS_TARGET`
3. Start the draft stack with:
   `docker compose -f grafana/docker-compose.yml --env-file grafana/.env up -d`

## What is included

- `docker-compose.yml`
  Prometheus, Grafana, Node Exporter, and cAdvisor
- `prometheus/prometheus.yml`
  Initial scrape targets
- `provisioning/`
  Auto-loaded datasource and dashboard providers
- `dashboards/system-overview.json`
  Initial dashboard draft

## Suggested next steps for the owner

- Confirm the backend metrics endpoint path and labels
- Add application-level metrics after system dashboards are stable
- Split dashboards into system, Kafka, and application views when metrics mature

## Notes

- The current draft is aimed at Docker on a Linux VM, especially for `cadvisor` host mounts.
- If the backend does not expose `/metrics` yet, keep the Prometheus job as a placeholder until the application metrics endpoint is ready.
