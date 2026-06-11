# Kafka Workstream

This directory is the shared workspace for Kafka-related performance work.

## Goal

- Final target: `100000` concurrent online users
- Estimated message load: `1000 msg/s`
- Practical approach: ramp up on local or VM first, find the ceiling, then estimate how many VMs are required

## Included Files

- `docker-compose.yml`
  Single-node Kafka draft stack plus Kafka UI
- `.env.example`
  Draft environment values for the local Kafka stack
- `load-profile.example.json`
  Staged load profile for ramp-up testing
- `scripts/run_kafka_load_test.py`
  Staged Kafka producer load-test runner
- `scripts/run_backend_message_burst_test.py`
  End-to-end backend burst runner that separates setup from the measured message-send phase
- `scripts/mock_slow_consumer.sh`
  Configurable mock consumer for fast capacity tests or slow lag demos
- `scripts/ws-online-users-template.js`
  Placeholder template for a future online-user soak runner

## How The Runner Works

`run_kafka_load_test.py` does not require an extra Kafka client library.

It runs `kafka-producer-perf-test.sh` inside the Kafka container and:

1. Creates or validates the test topic
2. Sends traffic in stages such as `100 -> 250 -> 500 -> 750 -> 1000 msg/s`
3. Stops when a stage cannot sustain the configured throughput threshold
4. Writes a JSON report under `kafka/reports/`
5. Estimates required Kafka VM count using the best sustainable throughput observed on the current machine

Keep the broker-level load-test topic separate from the real application topic.
`run_kafka_load_test.py` writes raw payloads that are not valid chat event JSON, so
its profile should use `chat.load-test.events`. The backend app and
`backend-consumer` should use `KAFKA_TOPIC_CHAT_EVENTS=chat.app.events`.

For end-to-end message pressure tests, use the backend burst runner instead.
The Docker app stack now routes `POST /chatrooms/{room_id}/messages` through Kafka:

```text
client -> backend API -> Kafka -> backend-consumer -> PostgreSQL
```

In the current demo-safe mode, the message API publishes to Kafka and waits for
`backend-consumer` to persist the message before returning the saved response.
This keeps the existing frontend behavior stable, but it also means API
throughput is limited by end-to-end Kafka consumer and PostgreSQL persistence.

Run this when you want producer, consumer, backend, and DB Grafana panels to move together:

```bash
python kafka/scripts/run_backend_message_burst_test.py \
  --base-url http://127.0.0.1:8000 \
  --users 1000 \
  --rooms 1000 \
  --messages-per-room 1 \
  --persistence-samples 50 \
  --prepare-concurrency 100 \
  --burst-concurrency 1000 \
  --request-timeout 60
```

This runner separates the setup work from the measured burst:

```text
prepare phase: register -> login -> create rooms
message burst phase: send messages only
```

The report includes `sendMessageRequestsPerSecond`, which represents the
end-to-end completed message throughput for the current synchronous persistence
mode.

This is useful when local or VM resources are limited and you want a safe way to find the ceiling gradually.

## Quick Start

1. Copy the environment file:

```bash
copy kafka\.env.example kafka\.env
```

If you are using Git Bash or WSL instead of PowerShell:

```bash
cp kafka/.env.example kafka/.env
```

2. Start Kafka:

```bash
docker compose -f kafka/docker-compose.yml --env-file kafka/.env up -d
```

3. Run the staged load test:

```bash
py -3 kafka/scripts/run_kafka_load_test.py --profile kafka/load-profile.example.json
```

4. Review the generated report in `kafka/reports/`

If you are on macOS or Linux, replace `py -3` with `python3`.

To run a consumer at the same time:

```bash
docker compose -f kafka/docker-compose.yml --env-file kafka/.env --profile consumer-demo up -d mock-slow-consumer
```

## Example Output Meaning

The runner prints one row per stage:

- `target msg/s`: the requested rate for that stage
- `actual msg/s`: the throughput that Kafka actually achieved
- `pass%`: achieved throughput divided by requested throughput
- `p95/p99/max`: latency distribution for that stage

If a stage falls below the configured `throughputPassRatio`, the runner stops there and treats the previous passing stage as the current sustainable ceiling.

## Common Commands

Run the default profile:

```bash
py -3 kafka/scripts/run_kafka_load_test.py --profile kafka/load-profile.example.json
```

Use custom stage rates:

```bash
py -3 kafka/scripts/run_kafka_load_test.py --profile kafka/load-profile.example.json --rates 100,300,600,900,1200
```

Shorten each stage to 30 seconds while exploring:

```bash
py -3 kafka/scripts/run_kafka_load_test.py --profile kafka/load-profile.example.json --stage-duration-seconds 30
```

Only print the Docker commands without actually running them:

```bash
py -3 kafka/scripts/run_kafka_load_test.py --profile kafka/load-profile.example.json --dry-run
```

Provide an observed online-user ceiling for a separate websocket soak result so the report also estimates app-tier VM count:

```bash
py -3 kafka/scripts/run_kafka_load_test.py --profile kafka/load-profile.example.json --observed-online-users-per-vm 8000
```

Start Kafka exporter for Grafana and Prometheus:

```bash
docker compose -f kafka/docker-compose.yml --env-file kafka/.env up -d kafka kafka-ui kafka-exporter
```

Start the mock consumer:

```bash
docker compose -f kafka/docker-compose.yml --env-file kafka/.env --profile consumer-demo up -d mock-slow-consumer
```

Scale mock consumers up to the topic partition count when testing consumer capacity:

```bash
docker compose -f kafka/docker-compose.yml --env-file kafka/.env --profile consumer-demo up -d --scale mock-slow-consumer=12 mock-slow-consumer
```

## Environment Fields

`kafka/.env.example` 是啟動 Kafka stack 時使用的環境參數範本。

- `KAFKA_CLUSTER_ID`: Kafka KRaft cluster ID。單機測試可使用固定字串；若重建 volume 後可沿用同一組設定。
- `KAFKA_BROKER_ID`: Kafka broker 節點 ID。單機 Kafka 通常設定為 `1`。
- `KAFKA_INTERNAL_PORT`: Docker network 內部服務互連使用的 Kafka port，例如 exporter、consumer、Kafka UI 會連這個 port。
- `KAFKA_CONTROLLER_PORT`: KRaft controller 使用的 port，負責 Kafka metadata quorum。
- `KAFKA_EXTERNAL_PORT`: 從本機或 VM 外部連進 Kafka 的 port，目前對應 container 內的 `9094`。
- `KAFKA_UI_PORT`: Kafka UI 對外 port，可用來在瀏覽器查看 topic、consumer group 等資訊。
- `KAFKA_EXPORTER_PORT`: Kafka exporter 對外 port，Prometheus 會 scrape exporter 的 `/metrics`。
- `KAFKA_ADVERTISED_HOST`: Kafka 對外 advertised listener 的 host。local 測試通常是 `localhost`；VM 測試可改成 VM IP 或 DNS。
- `KAFKA_TOPIC_CHAT_EVENTS`: 測試用 topic 名稱，目前是 `chat.events`。
- `KAFKA_TOPIC_PARTITIONS`: 測試 topic 的 partition 數量。partition 越多，越能平行處理 producer/consumer，但也會增加管理成本。
- `KAFKA_TOPIC_REPLICATION_FACTOR`: topic replication factor。local 單 broker 只能是 `1`；多 broker 才能設成 `2` 或 `3`。
- `KAFKA_TEST_DURATION_SECONDS`: 壓測目標總時長參考值，目前主要作為目標描述，實際 staged runner 使用 `load-profile.example.json` 的 `stageDurationSeconds`。
- `KAFKA_TARGET_MSG_RATE`: 目標訊息吞吐量，例如 `1000` 代表希望支援每秒 1000 筆 messages。
- `KAFKA_TARGET_ONLINE_USERS`: 目標同時在線人數，例如 `100000`。
- `KAFKA_MOCK_CONSUMER_GROUP`: mock consumer 使用的 consumer group 名稱；Grafana lag 也是看這個 group。
- `KAFKA_MOCK_CONSUME_DELAY_SECONDS`: mock consumer 每消費一筆後刻意 sleep 的秒數。測 VM 消化能力請用 `0`；示範 lag 上升可改成 `2` 或更高。
- `KAFKA_MOCK_MAX_POLL_RECORDS`: consumer 每次 poll 最多抓幾筆。數值越高，consumer 批次消化能力通常越好。
- `KAFKA_MOCK_LOG_EVERY_N`: mock consumer 每消費多少筆才印一次 log，避免大量 log IO 影響壓測。
- `KAFKA_MOCK_AUTO_OFFSET_RESET`: consumer group 沒有既有 offset 時從哪裡開始消費。`earliest` 代表從最早訊息開始，`latest` 代表只吃新訊息。

## Profile Fields

Topic names are controlled from the repo-level `.env`:

- `KAFKA_TOPIC_CHAT_EVENTS`: real app JSON message topic, used by backend and `backend-consumer`.
- `KAFKA_TOPIC_LOAD_TEST_EVENTS`: raw broker load-test topic, used by `run_kafka_load_test.py`.

`kafka/load-profile.example.json` intentionally does not define `topic`; the
runner reads `.env` and applies `KAFKA_TOPIC_LOAD_TEST_EVENTS`.

`kafka/load-profile.example.json` 是 Kafka staged load test 的主要壓測設定。

- `scenarioName`: 壓測情境名稱，會出現在 client id 與報表中，方便辨識本次測試。
- `topic`: producer 要寫入的 Kafka topic，目前是 `chat.events`。
- `partitions`: 建立 topic 時使用的 partition 數量。目前設定 `12`，代表 Grafana 的 `Lag by Partition` 會看到 12 條 partition lag。
- `replicationFactor`: topic replication factor。單 broker local/VM 測試只能使用 `1`。
- `bootstrapServer`: 壓測腳本在 Docker network 內連線 Kafka 的地址，目前是 `kafka:9092`。
- `messageSizeBytes`: 每筆測試訊息大小，單位 bytes。目前 `512` 表示每筆 message 約 512 bytes。
- `producerCount`: producer 數量參考值。目前 runner 使用單一 `kafka-producer-perf-test.sh` process；需要多 producer 時可另行擴充。
- `stageDurationSeconds`: 每個壓測階段持續秒數。現在 `60` 表示每個 rate 跑 60 秒。
- `stageRatesPerSecond`: 階段式加壓速率。現在 `[100, 250, 500, 750, 1000]` 表示逐步測到每秒 1000 筆。
- `targetMessageRatePerSecond`: 最終目標吞吐量，用於報表估算 VM 數量。目前是 `1000 msg/s`。
- `targetConcurrentOnlineUsers`: 最終目標同時在線人數，用於容量規劃描述與估算。
- `observedOnlineUsersPerVm`: 若另外做 WebSocket/online user soak test，可填入單台 VM 實測可承受在線人數，用於估算 app tier VM 數量。
- `acks`: producer 等待 Kafka ack 的策略。`1` 表示 leader 寫入成功就回應；吞吐較高，但可靠性低於 `all`。
- `compressionType`: producer 壓縮方式。`none` 不壓縮；可改 `gzip`、`snappy`、`lz4`、`zstd` 測試 CPU 與網路取捨。
- `batchSize`: producer batch 大小，單位 bytes。較大 batch 可能提高吞吐，但也可能增加延遲。
- `lingerMs`: producer 等待湊 batch 的時間，單位 ms。較高可提升 batch 效率，但會增加單筆訊息等待時間。
- `throughputPassRatio`: 每個 stage 的通過門檻。`0.9` 表示實際吞吐至少要達目標吞吐 90% 才算 PASS。
- `safetyFactor`: VM 數量估算時保留的安全係數。`0.7` 表示只把單台 VM 實測能力的 70% 當作可用容量。
- `notes`: 補充說明，不影響壓測執行。

## Kafka Observability

Grafana stack 目前包含一個 Kafka 專用 dashboard：

- `Producer Rate`
- `Consumer Rate`
- `Consumer Lag`
- `Backlog`
- `Produced vs Consumed Offsets`
- `Lag by Partition`

## Partition And Scaling

`Lag by Partition` 會依照 topic 的實際 partition 數量顯示每個 partition 的 lag。現在 `load-profile.example.json` 和 `.env.example` 都設定為 `12` 個 partitions，所以你應該會看到 12 個 partition 的 lag，而不是固定 10 個。

partition 和 scaling 有關，但不是「等於 scaling」。它比較像是 Kafka 平行處理的切分單位：

- producer 可以把訊息分散寫入多個 partitions，提高 broker 端平行寫入能力。
- consumer group 內的多個 consumer instance 可以分別負責不同 partitions，提高消費平行度。
- 同一個 consumer group 中，最多同時有效消費的 consumer 數量通常不會超過 partition 數量；例如 12 partitions 最多大約讓 12 個 consumers 同時各吃一部分。
- 如果 consumer 數量大於 partition 數，多出來的 consumers 通常會閒置，因為沒有 partition 可分配。
- 如果某個 partition lag 特別高，代表訊息分布或該 partition 消費速度可能不均，需要檢查 partition key、consumer 數量或 consumer 處理效能。

因此，增加 partitions 是 Kafka scaling 的一部分，但完整 scaling 還包含 broker 數量、consumer instance 數量、message key 分布、CPU、記憶體、磁碟 IO 與網路能力。

測試 VM consumer 消化能力時，請使用預設的全速模式：

- `KAFKA_MOCK_CONSUME_DELAY_SECONDS=0`
- `Consumer Rate` 應該接近或高於 `Producer Rate`
- `Consumer Lag` 和 `Backlog` 不應該持續成長；producer 停止後應該逐步下降到接近 `0`

如果只是要示範 Grafana 能看到 lag 上升，請讓 producer throughput 高於 mock consumer speed。例如：

- 壓測流量跑到 `500` 到 `1000 msg/s`
- mock consumer 每筆訊息延遲 `2` 秒

這會讓 produced offset 和 committed offset 拉開距離，Grafana 就會顯示上升中的 backlog 和 lag。

## VM Estimation Logic

報表使用以下概念估算 Kafka VM 數量：

```text
safe_rate_per_vm = best_observed_rate_per_vm * safetyFactor
estimated_kafka_vm_count = ceil(targetMessageRatePerSecond / safe_rate_per_vm)
```

範例：

- 如果單台 VM 實測可承受 `720 msg/s`
- 且 `safetyFactor = 0.7`
- 則單台 VM 的安全容量約為 `504 msg/s`
- 若目標是 `1000 msg/s`，估算結果就是 `ceil(1000 / 504) = 2` 台 VM

這只是容量規劃估算，不是 production 保證。正式採用前仍需要在實際 VM 規格、production-like network、storage 設定下重新測試。

## Notes

- 這支 runner 主要測 Kafka producer throughput；若要測 producer-consumer 是否整體消化得動，請搭配全速 mock consumer。
- `100000` 同時在線使用者仍需要另外透過 WebSocket、gateway 或 connection-soak tooling 驗證。
- 若要讓結果更接近 production，請讓 topic partitions、acks、batching、compression、disk、VM size 盡量貼近正式架構。
