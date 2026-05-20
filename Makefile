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

test-backend:
	docker compose exec backend pytest -v

test-backend-file:
	docker compose exec backend pytest -v $(FILE)

test-unit:
	docker compose exec backend pytest -m unit

test-smoke:
	docker compose exec backend pytest -m smoke
