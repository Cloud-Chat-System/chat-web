#!/bin/sh

set -eu

if [ "$#" -eq 0 ]; then
    exit 0
fi

repo_root=$(cd "$(dirname "$0")/.." && pwd)

set --
for file in "$@"; do
    case "$file" in
        backend/*.py)
            set -- "$@" "${file#backend/}"
            ;;
        *)
            ;;
    esac
done

if [ "$#" -eq 0 ]; then
    exit 0
fi

# Alive Docker Container
if docker compose -f "$repo_root/docker-compose.yml" ps --services --status running 2>/dev/null | grep -qx "backend"; then
    cd "$repo_root"
    docker compose exec -T backend python -m ruff check --fix "$@"
    docker compose exec -T backend python -m ruff format "$@"
    exit 0
fi

# Dead but reusable Docker image
if docker compose -f "$repo_root/docker-compose.yml" config >/dev/null 2>&1; then
    cd "$repo_root"
    docker compose run --rm -T backend python -m ruff check --fix "$@"
    docker compose run --rm -T backend python -m ruff format "$@"
    exit 0
fi

# .venv fallback
if [ -x "$repo_root/backend/.venv/bin/python" ] && "$repo_root/backend/.venv/bin/python" -m ruff --version >/dev/null 2>&1; then
    cd "$repo_root/backend"
    .venv/bin/python -m ruff check --fix "$@"
    .venv/bin/python -m ruff format "$@"
    exit 0
fi

# 本地全域 Python fallback
if command -v python3 >/dev/null 2>&1 && python3 -m ruff --version >/dev/null 2>&1; then
    cd "$repo_root/backend"
    python3 -m ruff check --fix "$@"
    python3 -m ruff format "$@"
    exit 0
fi

echo "No backend lint runtime found." >&2
echo "Backend hooks prefer Docker. Start Docker Compose or install ruff locally as a fallback." >&2
exit 1
