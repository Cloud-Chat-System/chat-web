# Testing Guide

This repo has five test/check layers:

1. Lint checks
2. Backend pytest tests
3. Frontend Vitest tests
4. Playwright E2E tests
5. Backend pressure tests

Root `package.json` provides the common shortcut commands. Some commands run inside Docker because the backend is Docker-first.

## Setup

Fresh clone:

```bash
npm ci
cd frontend && npm ci && cd ..
```

Most backend, E2E, and pressure commands also need Docker Desktop running.

## Lint Checks

### Backend Lint

Command:

```bash
npm run lint:backend
```

What it runs:

```bash
docker compose run --rm -T backend python -m ruff check app tests
```

Framework/tool:

- Ruff

What it checks:

- Python syntax-level and static-analysis issues
- unused imports
- undefined names
- selected Python style/error rules configured in `backend/ruff.toml`

This does not run the backend app and does not call test functions.

### Frontend Lint

Command:

```bash
npm run lint:frontend
```

What it runs:

```bash
npm --prefix frontend run lint
```

which runs:

```bash
eslint .
```

Framework/tool:

- ESLint
- React ESLint plugin
- React Hooks ESLint plugin

What it checks:

- JavaScript/JSX static issues
- invalid React hook usage
- unused/suspicious frontend code patterns
- React-specific lint rules

Generated folders like `coverage/`, `dist/`, and `node_modules/` are ignored.

## Backend Pytest Tests

Backend tests live under:

```text
backend/tests/
```

Framework/tool:

- pytest
- FastAPI `TestClient`
- SQLite test database for normal backend tests

The shared backend fixtures are in:

```text
backend/tests/conftest.py
```

They configure:

- test `DATABASE_URL`
- JWT test settings
- FastAPI test client
- automatic test database reset before each non-pressure test

### All Backend Tests Except Pressure

Command:

```bash
npm run test:backend
```

What it runs:

```bash
docker compose run --rm -T backend pytest -v
```

`backend/pytest.ini` excludes pressure tests by default:

```ini
addopts = -v -m "not pressure"
```

So this runs:

```text
unit + smoke
```

and skips:

```text
pressure
```

### Backend Unit Tests

Command:

```bash
npm run test:backend:unit
```

What it runs:

```bash
pytest -v -m unit
```

Files:

```text
backend/tests/unit/test_auth_utils.py
backend/tests/unit/test_health.py
```

What they test:

- password hashing and verification
- wrong password rejection
- JWT create/decode round trip
- invalid/expired token handling
- `/health` liveness endpoint
- `/api/health` readiness behavior

How they test:

- mostly direct function calls and FastAPI test-client requests
- `monkeypatch` is used to simulate database health success/failure
- Python `assert` statements define pass/fail

### Backend Smoke Tests

Command:

```bash
npm run test:backend:smoke
```

What it runs:

```bash
pytest -v -m smoke
```

Files:

```text
backend/tests/smoke/test_auth_flow.py
backend/tests/smoke/test_chatrooms_api.py
backend/tests/smoke/test_messages_api.py
backend/tests/smoke/test_realtime_flow.py
backend/tests/smoke/test_users_api.py
```

What they test:

- user register/login/profile/logout flow
- duplicate email/username rejection
- invalid login rejection
- simulated Google login account creation/reuse
- direct chat creation idempotency
- group chat creation rules
- malicious `creator_id` ignored by backend
- unread count and latest-message ordering
- send/list/mark-read message flow
- message pagination
- non-member message access rejection
- user search and user lookup
- WebSocket ping/pong
- online presence tracking
- realtime message/presence broadcast

How they test:

- use FastAPI `TestClient`, not a real browser
- use a temporary SQLite database
- call backend API endpoints directly
- open in-process WebSocket connections through the test client
- assert HTTP status codes, response bodies, database snapshots, and WebSocket messages

## Frontend Vitest Tests

Frontend tests live near frontend source files:

```text
frontend/src/**/*.test.js
frontend/src/**/*.test.jsx
```

Command:

```bash
npm run test:frontend
```

What it runs:

```bash
npm --prefix frontend run test
```

which runs:

```bash
vitest run
```

Framework/tools:

- Vitest
- React Testing Library
- jest-dom matchers
- jsdom fake browser environment

Config:

```text
frontend/vite.config.js
frontend/src/test/setup.js
```

### Validator Tests

File:

```text
frontend/src/utils/validators.test.js
```

Source tested:

```text
frontend/src/utils/validators.js
```

What they test:

- `validateEmail`
- `validatePassword`
- `validateName`
- `validatePasswordMatch`

How they test:

- call pure frontend functions directly
- no browser rendering
- no backend calls
- no password storage

Example criteria:

- `alice@example.com` is valid
- `alice` is invalid
- password length must be at least 6
- display name must be at least 2 trimmed characters
- password confirmation must match exactly

### Avatar Component Tests

File:

```text
frontend/src/components/common/Avatar.test.jsx
```

Source tested:

```text
frontend/src/components/common/Avatar.jsx
```

What they test:

- single-word initials
- multi-word initials
- image avatar rendering
- status indicator rendering

How they test:

- React Testing Library renders the component into jsdom
- tests query DOM output using `screen`
- jest-dom assertions verify rendered elements

### Auth Store Tests

File:

```text
frontend/src/store/useAuthStore.test.js
```

Source tested:

```text
frontend/src/store/useAuthStore.js
```

What they test:

- `initAuth`
- successful login
- failed login
- logout cleanup
- localStorage token handling
- Zustand user/error/loading state

How they test:

- mock `frontend/src/utils/api.js`
- fake backend success/failure responses
- do not call the real backend
- verify frontend behavior after mocked responses

Example mock scenario:

```text
api.post('/auth/login') returns token + user
frontend stores token in localStorage
frontend stores user in Zustand state
```

## Frontend Build Check

Command:

```bash
npm run build:frontend
```

What it runs:

```bash
npm --prefix frontend run build
```

which runs:

```bash
vite build
```

Tool:

- Vite

What it checks:

- React/JSX can compile
- imports resolve
- production bundle can be generated

This is not a test suite, but it catches build-time frontend failures.

## Playwright E2E Tests

E2E tests live under:

```text
e2e/tests/
```

Command:

```bash
npm run test:e2e
```

Framework/tool:

- Playwright
- Chromium
- real browser automation

Config:

```text
e2e/playwright.config.js
```

Local infrastructure:

```bash
docker compose up -d db
docker compose exec -T db pg_isready -U chat_user -d chat_app
docker compose up --build -d backend
npm run test:e2e
docker compose down
```

Playwright starts the frontend dev server automatically and points it at the local backend.

### Auth E2E

File:

```text
e2e/tests/auth.spec.js
```

What it tests:

- unauthenticated `/chat` redirects to `/login`
- user registers through browser UI
- user logs in through browser UI
- user logs out through browser UI

How it tests:

- fills real form inputs in Chromium
- uses unique email per run
- checks URL transitions
- checks logged-in user email appears

### Direct Chat E2E

File:

```text
e2e/tests/direct-chat.spec.js
```

What it tests:

- Alice and Bob are created through backend API setup
- Alice logs in through browser UI
- Alice creates a direct chat with Bob through browser UI
- Alice sends a message
- message appears in Alice's chat
- Bob logs in later and can read Alice's persisted message

How it tests:

- API setup creates users quickly
- browser actions test the actual UI flow
- selectors use `data-testid`
- message persistence is checked by logging in as the recipient

### Group Chat E2E

File:

```text
e2e/tests/group-chat.spec.js
```

What it tests:

- Alice, Bob, and Charlie are created through backend API setup
- Alice logs in through browser UI
- Alice opens group chat mode
- Alice selects Bob and Charlie
- Alice creates a group
- Alice sends a group message
- message appears in the group chat

How it tests:

- browser interacts with modal controls
- users are selected through search results
- group room is verified in the sidebar
- message bubble is verified in the chat window

## Backend Pressure Tests

Pressure tests live under:

```text
backend/tests/pressure/
```

Commands:

```bash
npm run test:pressure:light
npm run test:pressure:mid
npm run test:pressure:heavy
```

Custom:

```bash
npm run test:pressure -- --pressure-scenario custom --pressure-users 100 --pressure-rooms 100
```

Local infrastructure:

```bash
docker compose up -d db
docker compose exec -T db pg_isready -U chat_user -d chat_app
docker compose up --build -d backend
npm run test:pressure:light
docker compose down
```

Framework/tools:

- pytest wrapper
- async HTTP client via `httpx`
- WebSocket client via `websockets`
- live backend container
- live Postgres container

Source files:

```text
backend/tests/pressure/chat_pressure.py
backend/tests/pressure/test_pressure_scenarios.py
backend/tests/pressure/conftest.py
```

What they test:

- registration latency
- login latency
- WebSocket connection latency
- chatroom creation latency
- message write latency
- message-history query latency
- sampled persistence of stored messages
- total recorded errors

How they test:

- generate unique users
- register and login users through real backend HTTP API
- optionally open many WebSocket connections to simulate online users
- create direct or group rooms
- send many messages concurrently
- query message history repeatedly
- verify sampled latest messages are still retrievable

Metrics printed:

```text
p50
p95
p99
max
count
```

Criteria printed:

```text
PASS/FAIL per metric
actual value
threshold
margin from threshold
```

Examples:

```text
PASS register_p95           actual=  900.00ms threshold<= 1500.00ms margin=  600.00ms
FAIL send_message_p95       actual= 1300.00ms threshold<= 1000.00ms margin= -300.00ms
```

Preset criteria:

```text
light:
  register/login p95 <= 1500ms
  websocket/create/send/fetch/persist p95 <= 1000ms
  total errors <= 0

mid:
  register/login p95 <= 2500ms
  websocket/create/send/fetch/persist p95 <= 1500ms
  total errors <= 0

heavy:
  register/login p95 <= 5000ms
  websocket/create/send/fetch/persist p95 <= 3000ms
  errors are reported but not failed by default
```

Pressure tests are excluded from normal backend pytest runs:

```ini
addopts = -v -m "not pressure"
```

Run them explicitly with:

```bash
docker compose exec -T backend python -m pytest -s tests/pressure -m pressure --pressure-scenario light
```

## GitHub Actions

Normal CI:

```text
.github/workflows/ci.yml
```

Runs automatically on push and pull request:

```text
backend-lint-and-test
frontend-lint-test-and-build
e2e-test
```

Pressure workflow:

```text
.github/workflows/pressure.yml
```

Runs manually from:

```text
GitHub -> Actions -> Pressure Tests -> Run workflow
```

The pressure workflow:

1. starts Postgres
2. waits for `pg_isready`
3. starts backend
4. waits for `/api/health`
5. runs pytest pressure scenario
6. prints metrics and criteria
7. stops services
