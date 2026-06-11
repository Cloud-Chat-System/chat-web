# 如何在VM上啟動project
## Step 1 複製環境變數
```bash
cd chat-web
#複製環境設定檔
cp .env.example .env
cp kafka/.env.example kafka/.env
cp grafana/.env.example grafana/.env
```
## Step 2 修改/kafka/.env
- 把`KAFKA_ADVERTISED_HOST` 改成VMIP

## Step3 執行腳本會自動生成憑證&設定環境變數
- ./run_VM.sh

訪問website : http://VMIP:3000/ 
訪問grafana : https://VMIP:3001/

# 如何在VM上跑kafka壓測

## Step 1 修改環境變數
```bash
cd chat-web
```
修改.env 設定 `KAFKA_MESSAGE_FLOW_ENABLED=false`
## Step2 跑測試腳本
```bash
#測試1000msg/s
python3 kafka/scripts/run_backend_message_burst_test.py --base-url http://127.0.0.1:8000 --users 1000 --rooms 1000 --messages-per-room 1 --persistence-samples 50 --persistence-wait-seconds 60 --prepare-concurrency 100 --burst-concurrency 1000 --request-timeout 60
```
# DEMO vedio
grafana demo vedio : https://youtu.be/YAtnq4d0Vd0
kafka stress test vedio : https://youtu.be/cNAo0iteeWs