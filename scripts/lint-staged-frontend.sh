#!/bin/sh

set -eu

if [ "$#" -eq 0 ]; then
    exit 0
fi

repo_root=$(cd "$(dirname "$0")/.." && pwd)

set --
for file in "$@"; do
    case "$file" in
        frontend/*)
            set -- "$@" "${file#frontend/}"
            ;;
    esac
done

if [ "$#" -eq 0 ]; then
    exit 0
fi

if [ -x "$repo_root/frontend/node_modules/.bin/eslint" ]; then
    cd "$repo_root/frontend"
    ./node_modules/.bin/eslint --fix "$@"
    exit 0
fi

if docker compose -f "$repo_root/docker-compose.yml" ps --services --status running 2>/dev/null | grep -qx "frontend"; then
    cd "$repo_root"
    docker compose exec -T frontend npx eslint --fix "$@"
    exit 0
fi

if docker compose -f "$repo_root/docker-compose.yml" config >/dev/null 2>&1; then
    cd "$repo_root"
    docker compose run --rm -T frontend npx eslint --fix "$@"
    exit 0
fi

echo "No frontend lint runtime found." >&2
echo "Run npm install in frontend or make Docker Compose available before committing." >&2
exit 1
