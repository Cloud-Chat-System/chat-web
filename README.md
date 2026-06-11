# branch 介紹
- main : 可在local測試的完成版
- dev : 開發測試階段用來merge PR，確認目前功能完整就會merge到main
- deploy/vm-integration-testing : 可在VM上測試的完成版

# 如何啟動project
```bash
cd chat-web
#複製環境設定檔
cp .env.example .env
cp kafka/.env.example kafka/.env
cp grafana/.env.example grafana/.env

docker stop $(docker ps -q)
docker compose up --build -d
docker compose -f kafka/docker-compose.yml --env-file kafka/.env up -d kafka kafka-ui kafka-exporter
docker compose -f grafana/docker-compose.yml --env-file grafana/.env up -d
```
訪問website : http://localhost:3000/ 
prometheus : http://localhost:9090/targets
grafana 監控 (預設帳密都是admin): http://localhost:3003/ 

# Grafana 監控
有兩個監控面板 :
- Chat Web Minimal Observability : 主要負責監控我們的TSMC messenger的流量
- Kafka Producer Consumer Lag : 主要是負責監控kafka壓測過程
p.s. local 測試時grafana都會抓不到cpu rate & container memory 但deploy上VM後都沒問題請觀看 [grafana demo vedio](https://youtu.be/YAtnq4d0Vd0)


# kafka壓測
因為kafka 壓測開發過程是先在local端測試，再deploy到VM上測試，deploy到VM後發現有些bug功能不夠完整就直接在VM上修改了，因為時間關係來不及同步修改到main，所以可以參考 deploy/vm-integration-testing branch `/kafka`[kafka demo vedio](https://youtu.be/cNAo0iteeWs)

```bash
# 壓力測試1000msg/s
python3 kafka/scripts/run_backend_message_burst_test.py --base-url http://127.0.0.1:8000 --users 1000 --rooms 1000 --messages-per-room 1 --persistence-samples 50 --persistence-wait-seconds 60 --prepare-concurrency 100 --burst-concurrency 1000 --request-timeout 60
```
# DEMO vedio
grafana demo vedio : https://youtu.be/YAtnq4d0Vd0
kafka stress test vedio : https://youtu.be/cNAo0iteeWs

# 快捷指令列表
| Make 指令         | 實際 Docker 指令                                          | 用途                           |
| --------------- | ----------------------------------------------------- | ---------------------------- |
| `make ps`       | `docker compose ps`                                   | 查看 containers 狀態             |
| `make dev`      | `docker compose up --build`                           | build 並啟動服務，log 顯示在前景，ctrl-C會自動停掉服務       |
| `make dev-d`    | `docker compose up --build -d`                        | build 並在背景啟動服務               |
| `make logs`     | `docker compose logs -f`                              | 查看即時 logs                    |
| `make watch`    | `docker compose watch`                                | 監控任何frontend & backend修改自動rebuild            |
| `make down`     | `docker compose down`                                 | 停止並移除 containers，但保留 volumes (database) |
| `make reset-db` | `docker compose down -v && docker compose up --build -d` | 刪除 volumes，重建資料庫並啟動服務        |
---
# Frontend & Backend Code Convergence

**Main Branch:** [![codecov](https://codecov.io/gh/Cloud-Chat-System/chat-web/graph/badge.svg?token=P18Y0ZGGHI)](https://codecov.io/gh/Cloud-Chat-System/chat-web)
**ci-and-lint Branch:** [![codecov](https://codecov.io/gh/Cloud-Chat-System/chat-web/branch/ci-and-lint/graph/badge.svg?token=P18Y0ZGGHI)](https://codecov.io/gh/Cloud-Chat-System/chat-web)
