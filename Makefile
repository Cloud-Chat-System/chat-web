dev:
	docker compose up --build

dev-d:
	docker compose up --build -d 

watch:
	docker compose watch

down:
	docker compose down

reset-db:
	docker compose down -v
	docker compose up --build -d

logs:
	docker compose logs -f

ps:
	docker compose ps