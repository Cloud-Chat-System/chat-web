#!/usr/bin/env bash
set -euo pipefail

VMIP="$(curl -s https://ifconfig.me)"

mkdir -p certs nginx/conf.d

openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
  -keyout certs/chat-web.key \
  -out certs/chat-web.crt \
  -subj "/CN=${VMIP}" \
  -addext "subjectAltName = IP:${VMIP}"

sed -i "s|^FRONTEND_URL=.*|FRONTEND_URL=https://${VMIP}|" .env
sed -i "s|^VITE_API_BASE_URL=.*|VITE_API_BASE_URL=https://${VMIP}|" .env
sed -i "s|^VITE_WS_URL=.*|VITE_WS_URL=wss://${VMIP}/ws|" .env
sed -i "s|^CORS_ALLOWED_ORIGINS=.*|CORS_ALLOWED_ORIGINS=https://${VMIP}|" .env
sed -i "s|^KAFKA_ADVERTISED_HOST=.*|KAFKA_ADVERTISED_HOST=${VMIP}|" .env

docker stop $(docker ps -q)
docker compose -f grafana/docker-compose.yml --env-file grafana/.env up -d
docker compose up --build -d
docker compose -f kafka/docker-compose.yml --env-file kafka/.env up -d kafka kafka-ui kafka-exporter

