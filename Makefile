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

kafka-up:
	docker compose -f kafka/docker-compose.yml --env-file kafka/.env up -d

kafka-down:
	docker compose -f kafka/docker-compose.yml --env-file kafka/.env down

kafka-logs:
	docker compose -f kafka/docker-compose.yml --env-file kafka/.env logs -f

grafana-up:
	docker compose -f grafana/docker-compose.yml --env-file grafana/.env up -d

grafana-down:
	docker compose -f grafana/docker-compose.yml --env-file grafana/.env down

grafana-logs:
	docker compose -f grafana/docker-compose.yml --env-file grafana/.env logs -f

test-backend:
	docker compose exec backend pytest -v

test-backend-file:
	docker compose exec backend pytest -v $(FILE)

test-unit:
	docker compose exec backend pytest -m unit

test-smoke:
	docker compose exec backend pytest -m smoke
