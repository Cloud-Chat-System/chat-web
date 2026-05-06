# 如何啟動docker
- 只要更新frontend & backend code都需要重新執行以下指令
```bash
#確認chat-web是否已經跑起來了，避免重複build
docker ps
#若還沒有跑起來，啟動 
docker compose up --build
#關掉
docker compose down
```
訪問website : http://140.114.91.23:3000/ 確認frontend有成功連接到backend & database

# 查看databse中已經存放的資料
```bash
# 執行container中的database
docker compose exec db psql -U chat_user -d chat_app

SELECT * FROM users;
SELECT * FROM chat_rooms;
SELECT * FROM chat_room_members;
SELECT * FROM messages;
SELECT * FROM notifications;
SELECT * FROM user_presence;
```
# 快捷指令列表
一般開發使用
```bash
make dev-d
make logs
```
如果修改了 database schema 或 seed data，才使用，避免誤刪除資料庫資料。：
```bash
make reset-db
```

| Make 指令         | 實際 Docker 指令                                          | 用途                           |
| --------------- | ----------------------------------------------------- | ---------------------------- |
| `make dev`      | `docker compose up --build`                           | build 並啟動服務，log 顯示在前景        |
| `make dev-d`    | `docker compose up --build -d`                        | build 並在背景啟動服務               |
| `make down`     | `docker compose down`                                 | 停止並移除 containers，但保留 volumes |
| `make reset-db` | `docker compose down -v && docker compose up --build` | 刪除 volumes，重建資料庫並啟動服務        |
| `make logs`     | `docker compose logs -f`                              | 查看即時 logs                    |
| `make ps`       | `docker compose ps`                                   | 查看 containers 狀態             |

- `make dev` 在啟動前重新build image 並且啟動所有docker compose services (frontend / backend / database)
    - 使用時機 : 
        - 第一次啟動專案
        - 修改了 backend , frontend dependencies , Dockerfile
- `make dev-d` 在背景重新build image 並且啟動所有docker compose services
    - 使用時機 : 
        - 適合想讓服務在背景持續執行時使用。
        - 開發時不想讓 terminal 被 log 佔住想啟動服務後繼續在同一個 terminal 下其他指令。
        - VM server 上長時間啟動專案 。
        - Demo 或測試環境需要背景執行服務
- `make logs` 查看所有 frontend / backend / db 的即時 log。
    - 使用時機 : 
- `make down` 停止並移除目前 Docker Compose 建立的 containers、networks，但是保留volume(database)。
    - 使用時機 : 
        - 結束開發
        - 想重新啟動所有 containers
        - 修改了 compose 設定後想乾淨重開
        - 想釋放 VM 或本機資源
- `make reset-db` 停止並移除 containers、networks，以及 Docker volumes (database)，接著重新 build 並啟動服務。
   - 使用時機 :
        - 需要重置資料庫時使用。 
        - 修改了 database/init.sql
        - 修改了 database/seed.sql
        - 想重新建立乾淨的 database
        - schema 改壞了，需要重建
        - 測試假資料想更新
- `make ps` 查看目前 Docker Compose services 的執行狀態。
   - 使用時機 :
        - 確認 backend 是否 running
        - 確認 database 是否 healthy
        - 確認 frontend/nginx port 是否有被 expose
        - 確認 container 是否因錯誤退出

