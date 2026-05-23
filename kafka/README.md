# Kafka Workstream

This directory is the shared workspace for Kafka-related performance work.

## Scope

- Steady-state throughput test target: `1000 msg/s`
- Online-user target: `100000` concurrent users
- Single-repo convention: keep Kafka configs, scripts, and test profiles here

## Quick start

1. Copy `kafka/.env.example` to `kafka/.env`
2. Review topic and port settings
3. Start the draft stack with:
   `docker compose -f kafka/docker-compose.yml --env-file kafka/.env up -d`

## What is included

- `docker-compose.yml`
  Single-node Kafka draft stack plus Kafka UI
- `load-profile.example.json`
  Baseline test target profile
- `scripts/ws-online-users-template.js`
  A placeholder script for large online-user connection simulation

## Suggested next steps for the owner

- Replace the placeholder script with the actual test runner the team chooses
- Decide whether the `100000` online users should be simulated through WebSocket, gateway, or synthetic connection service
- Define producer batching, acks, compression, and partition key strategy
