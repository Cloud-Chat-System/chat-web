#!/bin/bash
set -eu

BOOTSTRAP_SERVER="${KAFKA_BOOTSTRAP_SERVER:-kafka:9092}"
TOPIC="${KAFKA_TOPIC:-chat.events}"
CONSUMER_GROUP="${KAFKA_CONSUMER_GROUP:-mock-slow-consumer}"
DELAY_SECONDS="${KAFKA_CONSUME_DELAY_SECONDS:-0}"
MAX_POLL_RECORDS="${KAFKA_MAX_POLL_RECORDS:-500}"
LOG_EVERY_N="${KAFKA_LOG_EVERY_N:-10000}"
AUTO_OFFSET_RESET="${KAFKA_AUTO_OFFSET_RESET:-earliest}"
KAFKA_BIN="/opt/bitnami/kafka/bin"
COUNT=0

echo "Starting mock consumer"
echo "bootstrap_server=${BOOTSTRAP_SERVER}"
echo "topic=${TOPIC}"
echo "consumer_group=${CONSUMER_GROUP}"
echo "delay_seconds=${DELAY_SECONDS}"
echo "max_poll_records=${MAX_POLL_RECORDS}"
echo "log_every_n=${LOG_EVERY_N}"
echo "auto_offset_reset=${AUTO_OFFSET_RESET}"

while true; do
  set +e
  "${KAFKA_BIN}/kafka-console-consumer.sh" \
    --bootstrap-server "${BOOTSTRAP_SERVER}" \
    --topic "${TOPIC}" \
    --group "${CONSUMER_GROUP}" \
    --consumer-property "auto.offset.reset=${AUTO_OFFSET_RESET}" \
    --consumer-property "enable.auto.commit=true" \
    --consumer-property "auto.commit.interval.ms=1000" \
    --consumer-property "max.poll.records=${MAX_POLL_RECORDS}" \
    2>/dev/stderr | while IFS= read -r message; do
      if [ -n "${message}" ]; then
        COUNT=$((COUNT + 1))
        if [ "${LOG_EVERY_N}" -gt 0 ] && [ $((COUNT % LOG_EVERY_N)) -eq 0 ]; then
          echo "[$(date -Iseconds)] consumed_count=${COUNT}"
        fi
        if [ "${DELAY_SECONDS}" != "0" ] && [ "${DELAY_SECONDS}" != "0.0" ]; then
          sleep "${DELAY_SECONDS}"
        fi
      fi
    done
  STATUS=$?
  set -e

  echo "Consumer stream ended with status ${STATUS}; reconnecting in 2s"
  sleep 2
done
