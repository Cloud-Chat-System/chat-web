dev:
	docker compose up --build

dev-d:
	docker compose up --build -d

down:
	docker compose down

reset-db:
	docker compose down -v
	docker compose up --build

logs:
	docker compose logs -f

ps:
	docker compose ps