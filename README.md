# 如何啟動docker
```bash
cd chat-web
#複製環境設定檔
cp .env.example .env
#確認chat-web docker 是否已經跑起來了(看到chat-web-frontend, chat-web-backend ,postgres:16.6 image)，避免重複build
docker ps
#若還沒有跑起來，build image
docker compose up --build -d
#若已經跑起來執行watch監控你的修改並主動rebuild
docker compose watch
#關掉docker
docker compose down
```
訪問website : http://localhost:3000/ 確認frontend有成功連接到backend & database

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
# 如果修改了database需要重新build
```bash
make reset-db
```
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


