.PHONY: \
		dev dev-d watch down reset-db logs ps \
		setup install-deps install-hooks install-frontend-deps pre-commit-check \
		lint lint-backend lint-frontend \
		test test-all test-backend test-frontend test-e2e test-e2e-ui test-backend-file test-unit test-smoke \
		ci-test-simulate-Github-backend ci-test-simulate-Github-frontend ci-test-simulate-Github-all

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

setup: install-hooks install-frontend-deps
	@echo "🟢 [Success] 本地 Hooks 與前端依賴初始化完畢，backend 維持 Docker-first。"

install-deps: setup

install-hooks:
	npm install

install-frontend-deps:
	cd frontend && npm install

pre-commit-check:
	npm run lint-staged

# Lint
lint: lint-backend lint-frontend

lint-backend:
	@if docker compose ps --services --status running 2>/dev/null | grep -qx "backend"; then \
		echo "ℹ️  backend 採 Docker-first，使用執行中的 backend 容器檢查..."; \
		docker compose exec -T backend python -m ruff check app tests; \
	else \
		echo "ℹ️  backend 採 Docker-first，啟動一次性 backend 容器檢查..."; \
		docker compose run --rm -T backend python -m ruff check app tests; \
	fi

lint-frontend:
	@if [ -d frontend/node_modules ]; then \
		cd frontend && npm run lint; \
	elif docker compose ps --services --status running 2>/dev/null | grep -qx "frontend"; then \
		echo "⚠️  本地未安裝前端相依套件，改用 Docker 容器執行..."; \
		docker compose exec -T frontend npm run lint; \
	else \
		echo "⚠️  本地未安裝前端相依套件，改用 Docker 容器執行..."; \
		docker compose run --rm -T frontend npm run lint; \
	fi

# Tests
test: test-unit test-smoke

test-all: test-backend test-frontend

test-backend:
	@if docker compose ps --services --status running | grep -qx "backend"; then \
		docker compose exec -T backend pytest -v; \
	else \
		docker compose run --rm -T backend pytest -v; \
	fi

test-unit:
	@if docker compose ps --services --status running | grep -qx "backend"; then \
		docker compose exec -T backend pytest -v -m unit; \
	else \
		docker compose run --rm -T backend pytest -v -m unit; \
	fi

test-smoke:
	@if docker compose ps --services --status running | grep -qx "backend"; then \
		docker compose exec -T backend pytest -v -m smoke; \
	else \
		docker compose run --rm -T backend pytest -v -m smoke; \
	fi

test-frontend:
	@if [ -d frontend/node_modules ]; then \
		cd frontend && npm run test; \
	elif docker compose ps --services --status running 2>/dev/null | grep -qx "frontend"; then \
		docker compose exec -T frontend npm run test; \
	else \
		docker compose run --rm -T frontend npm run test; \
	fi

test-e2e:
	docker compose up -d db
	@for i in $$(seq 1 30); do \
		if docker compose exec -T db pg_isready -U chat_user -d chat_app; then \
			break; \
		fi; \
		if [ "$$i" -eq 30 ]; then \
			docker compose logs db; \
			exit 1; \
		fi; \
		sleep 2; \
	done
	docker compose up --build -d backend
	@status=0; npm run test:e2e || status=$$?; docker compose down; exit $$status

test-e2e-ui:
	npm run test:e2e:ui


test-backend-file:
ifndef FILE
	$(error FILE is required. Usage: make test-backend-file FILE=tests/unit/test_auth_utils.py)
endif
	@if docker compose ps --services --status running | grep -qx "backend"; then \
		docker compose exec -T backend pytest -v $(FILE); \
	else \
		docker compose run --rm -T backend pytest -v $(FILE); \
	fi

ci-test-simulate-Github-backend:
	@if command -v act >/dev/null 2>&1; then \
		act -j backend-lint-and-test --container-architecture linux/amd64; \
	else \
		echo "❌ 錯誤：本地未安裝 act。請先執行 'brew install act' (Mac) 或對應安裝指令。"; \
		exit 1; \
	fi

ci-test-simulate-Github-frontend:
	@if command -v act >/dev/null 2>&1; then \
		act -j frontend-lint-and-build --container-architecture linux/amd64; \
	else \
		echo "❌ 錯誤：本地未安裝 act。"; \
		exit 1; \
	fi

ci-test-simulate-Github-all:
	@if command -v act >/dev/null 2>&1; then \
		act --container-architecture linux/amd64; \
	else \
		echo "❌ 錯誤：本地未安裝 act。"; \
		exit 1; \
	fi
