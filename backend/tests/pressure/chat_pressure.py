"""Pressure test engine for backend chat and presence flows."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import sys
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

import httpx
import websockets


GREEN = "\033[32m"
RED = "\033[31m"
RESET = "\033[0m"


DEFAULT_ARGS = {
    "base_url": "http://127.0.0.1:8000",
    "ws_url": None,
    "prefix": "pressure",
    "users": 50,
    "online_users": 10,
    "rooms": 50,
    "room_type": "direct",
    "group_size": 5,
    "messages_per_room": 5,
    "history_fetches": 50,
    "history_limit": 50,
    "persistence_samples": 10,
    "concurrency": 25,
    "request_timeout": 30.0,
    "wait_timeout": 60,
    "max_p95_ms": 0.0,
    "max_register_p95_ms": 0.0,
    "max_login_p95_ms": 0.0,
    "max_ws_connect_p95_ms": 0.0,
    "max_create_room_p95_ms": 0.0,
    "max_send_message_p95_ms": 0.0,
    "max_fetch_messages_p95_ms": 0.0,
    "max_verify_persist_p95_ms": 0.0,
    "max_errors": 0,
    "fail_on_errors": False,
}


def make_args(**overrides: Any) -> argparse.Namespace:
    values = {**DEFAULT_ARGS, **overrides}
    return argparse.Namespace(**values)


@dataclass
class User:
    username: str
    email: str
    password: str
    display_name: str
    user_id: int | None = None
    token: str | None = None


@dataclass
class Room:
    room_id: int
    member_indexes: list[int]
    last_message: str | None = None


class Metrics:
    def __init__(self) -> None:
        self.timings: dict[str, list[float]] = defaultdict(list)
        self.errors: dict[str, int] = defaultdict(int)

    def record(self, name: str, elapsed_ms: float) -> None:
        self.timings[name].append(elapsed_ms)

    def error(self, name: str) -> None:
        self.errors[name] += 1

    @property
    def error_count(self) -> int:
        return sum(self.errors.values())

    def p95(self, name: str) -> float:
        return self.percentile(name, 95)

    def percentile(self, name: str, percentile: int) -> float:
        values = sorted(self.timings.get(name, []))
        if not values:
            return 0.0
        index = max(0, min(len(values) - 1, int((percentile / 100) * len(values) + 0.999) - 1))
        return values[index]

    def print_summary(self) -> None:
        print("\n=== Pressure Summary ===")
        for name in sorted(self.timings):
            values = self.timings[name]
            if not values:
                continue
            sorted_values = sorted(values)
            p50 = statistics.median(sorted_values)
            p95 = self.p95(name)
            p99 = self.percentile(name, 99)
            print(
                f"{name:18} count={len(values):5d} "
                f"p50={p50:8.2f}ms p95={p95:8.2f}ms "
                f"p99={p99:8.2f}ms max={max(sorted_values):8.2f}ms"
            )

        if self.errors:
            print("\n=== Errors ===")
            for name, count in sorted(self.errors.items()):
                print(f"{name:18} errors={count}")


@dataclass
class CriterionResult:
    name: str
    actual: float
    threshold: float
    unit: str
    passed: bool


def collect_criteria(metrics: Metrics, args: argparse.Namespace) -> list[CriterionResult]:
    criteria = [
        ("register", args.max_register_p95_ms),
        ("login", args.max_login_p95_ms),
        ("ws_connect", args.max_ws_connect_p95_ms),
        ("create_room", args.max_create_room_p95_ms),
        ("send_message", args.max_send_message_p95_ms or args.max_p95_ms),
        ("fetch_messages", args.max_fetch_messages_p95_ms),
        ("verify_persist", args.max_verify_persist_p95_ms),
    ]
    results = [
        CriterionResult(
            name=f"{name}_p95",
            actual=metrics.p95(name),
            threshold=threshold,
            unit="ms",
            passed=metrics.p95(name) <= threshold,
        )
        for name, threshold in criteria
        if threshold
    ]

    if args.fail_on_errors:
        results.append(
            CriterionResult(
                name="total_errors",
                actual=float(metrics.error_count),
                threshold=float(args.max_errors),
                unit="count",
                passed=metrics.error_count <= args.max_errors,
            )
        )
    return results


def print_criteria(results: list[CriterionResult]) -> None:
    if not results:
        print("\n=== Pressure Criteria ===")
        print("No pass/fail criteria configured; metrics only.")
        return

    print("\n=== Pressure Criteria ===")
    use_color = os.getenv("NO_COLOR") is None and os.getenv("TERM") != "dumb"
    for result in results:
        symbol = "✓" if result.passed else "✗"
        status = "PASS" if result.passed else "FAIL"
        label = f"{symbol} {status}"
        if use_color:
            color = GREEN if result.passed else RED
            label = f"{color}{label}{RESET}"
        distance = result.threshold - result.actual
        print(
            f"{label:15} {result.name:22} "
            f"actual={result.actual:8.2f}{result.unit} "
            f"threshold<={result.threshold:8.2f}{result.unit} "
            f"margin={distance:8.2f}{result.unit}"
        )


async def measured(metrics: Metrics, name: str, coro: Any) -> Any:
    start = time.perf_counter()
    try:
        result = await coro
        metrics.record(name, (time.perf_counter() - start) * 1000)
        return result
    except Exception:
        metrics.error(name)
        raise


async def wait_for_backend(base_url: str, timeout_seconds: int) -> None:
    deadline = time.perf_counter() + timeout_seconds
    async with httpx.AsyncClient(base_url=base_url, timeout=5.0) as client:
        while time.perf_counter() < deadline:
            try:
                response = await client.get("/api/health")
                if response.status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            await asyncio.sleep(1)
    raise RuntimeError(f"Backend did not become ready within {timeout_seconds}s")


async def run_limited(items: list[Any], concurrency: int, worker) -> list[Any]:
    semaphore = asyncio.Semaphore(concurrency)

    async def run_one(item):
        async with semaphore:
            return await worker(item)

    return await asyncio.gather(*(run_one(item) for item in items))


def make_users(count: int, prefix: str) -> list[User]:
    run_id = uuid.uuid4().hex[:10]
    return [
        User(
            username=f"{prefix}_{run_id}_{index}",
            email=f"{prefix}-{run_id}-{index}@example.com",
            password="password123",
            display_name=f"{prefix} User {index}",
        )
        for index in range(count)
    ]


async def register_users(
    client: httpx.AsyncClient,
    users: list[User],
    concurrency: int,
    metrics: Metrics,
) -> None:
    async def register(user: User) -> None:
        response = await measured(
            metrics,
            "register",
            client.post(
                "/auth/register",
                json={
                    "username": user.username,
                    "email": user.email,
                    "password": user.password,
                    "display_name": user.display_name,
                },
            ),
        )
        response.raise_for_status()
        user.user_id = response.json()["user_id"]

    await run_limited(users, concurrency, register)


async def login_users(
    client: httpx.AsyncClient,
    users: list[User],
    concurrency: int,
    metrics: Metrics,
) -> None:
    async def login(user: User) -> None:
        response = await measured(
            metrics,
            "login",
            client.post("/auth/login", json={"email": user.email, "password": user.password}),
        )
        response.raise_for_status()
        payload = response.json()
        user.token = payload["token"]
        user.user_id = payload["user"]["id"]

    await run_limited(users, concurrency, login)


def auth_headers(user: User) -> dict[str, str]:
    if not user.token:
        raise RuntimeError(f"User {user.email} has no token")
    return {"Authorization": f"Bearer {user.token}"}


async def create_rooms(
    client: httpx.AsyncClient,
    users: list[User],
    room_count: int,
    room_type: str,
    group_size: int,
    concurrency: int,
    metrics: Metrics,
) -> list[Room]:
    room_specs: list[tuple[int, list[int]]] = []
    for index in range(room_count):
        creator_index = index % len(users)
        if room_type == "group":
            member_indexes = [
                (creator_index + offset + 1) % len(users)
                for offset in range(max(1, group_size - 1))
            ]
        else:
            member_indexes = [(creator_index + 1) % len(users)]
        room_specs.append((creator_index, member_indexes))

    async def create(spec: tuple[int, list[int]]) -> Room:
        creator_index, member_indexes = spec
        creator = users[creator_index]
        payload = {
            "room_type": room_type,
            "member_ids": [users[index].user_id for index in member_indexes],
        }
        if room_type == "group":
            payload["name"] = f"Pressure Group {uuid.uuid4().hex[:8]}"

        response = await measured(
            metrics,
            "create_room",
            client.post("/chatrooms", json=payload, headers=auth_headers(creator)),
        )
        response.raise_for_status()
        return Room(
            room_id=response.json()["id"],
            member_indexes=[creator_index, *member_indexes],
        )

    return await run_limited(room_specs, concurrency, create)


async def send_messages(
    client: httpx.AsyncClient,
    users: list[User],
    rooms: list[Room],
    messages_per_room: int,
    concurrency: int,
    metrics: Metrics,
) -> None:
    jobs = [
        (room, message_index)
        for room in rooms
        for message_index in range(messages_per_room)
    ]

    async def send(job: tuple[Room, int]) -> None:
        room, message_index = job
        sender_index = room.member_indexes[message_index % len(room.member_indexes)]
        sender = users[sender_index]
        content = f"pressure room={room.room_id} msg={message_index} id={uuid.uuid4().hex[:10]}"
        response = await measured(
            metrics,
            "send_message",
            client.post(
                f"/chatrooms/{room.room_id}/messages",
                json={"content": content},
                headers=auth_headers(sender),
            ),
        )
        response.raise_for_status()
        room.last_message = content

    await run_limited(jobs, concurrency, send)


async def fetch_histories(
    client: httpx.AsyncClient,
    users: list[User],
    rooms: list[Room],
    fetches: int,
    limit: int,
    concurrency: int,
    metrics: Metrics,
) -> None:
    jobs = [rooms[index % len(rooms)] for index in range(fetches)]

    async def fetch(room: Room) -> None:
        reader = users[room.member_indexes[0]]
        response = await measured(
            metrics,
            "fetch_messages",
            client.get(
                f"/chatrooms/{room.room_id}/messages",
                params={"limit": limit},
                headers=auth_headers(reader),
            ),
        )
        response.raise_for_status()

    await run_limited(jobs, concurrency, fetch)


async def verify_persistence(
    client: httpx.AsyncClient,
    users: list[User],
    rooms: list[Room],
    sample_size: int,
    metrics: Metrics,
) -> int:
    failures = 0
    for room in rooms[:sample_size]:
        if not room.last_message:
            continue
        reader = users[room.member_indexes[0]]
        response = await measured(
            metrics,
            "verify_persist",
            client.get(
                f"/chatrooms/{room.room_id}/messages",
                params={"limit": 200},
                headers=auth_headers(reader),
            ),
        )
        response.raise_for_status()
        messages = response.json()["messages"]
        contents = {message["content"] for message in messages}
        if room.last_message not in contents:
            failures += 1
    return failures


async def open_websockets(
    users: list[User],
    ws_url: str,
    online_count: int,
    metrics: Metrics,
) -> list[Any]:
    sockets = []
    for user in users[:online_count]:
        start = time.perf_counter()
        try:
            websocket = await websockets.connect(ws_url)
            await websocket.send(json.dumps({"token": user.token}))
            message = json.loads(await websocket.recv())
            if message.get("type") != "connected":
                raise RuntimeError(f"Unexpected websocket handshake payload: {message}")
            metrics.record("ws_connect", (time.perf_counter() - start) * 1000)
            sockets.append(websocket)
        except Exception:
            metrics.error("ws_connect")
            raise
    return sockets


async def close_websockets(sockets: list[Any]) -> None:
    await asyncio.gather(*(socket.close() for socket in sockets), return_exceptions=True)


async def run(args: argparse.Namespace) -> int:
    metrics = Metrics()
    users = make_users(args.users, args.prefix)
    ws_url = args.ws_url or args.base_url.replace("http", "ws", 1).rstrip("/") + "/ws"

    print("=== Pressure Scenario ===")
    print(f"base_url={args.base_url}")
    print(f"users={args.users} online_users={args.online_users}")
    print(f"rooms={args.rooms} room_type={args.room_type} group_size={args.group_size}")
    print(f"messages_per_room={args.messages_per_room}")
    print(f"history_fetches={args.history_fetches} history_limit={args.history_limit}")
    print(f"concurrency={args.concurrency}")

    await wait_for_backend(args.base_url, args.wait_timeout)
    sockets = []
    async with httpx.AsyncClient(base_url=args.base_url, timeout=args.request_timeout) as client:
        await register_users(client, users, args.concurrency, metrics)
        await login_users(client, users, args.concurrency, metrics)
        if args.online_users:
            sockets = await open_websockets(users, ws_url, args.online_users, metrics)

        rooms = await create_rooms(
            client,
            users,
            args.rooms,
            args.room_type,
            args.group_size,
            args.concurrency,
            metrics,
        )
        await send_messages(client, users, rooms, args.messages_per_room, args.concurrency, metrics)

        if args.history_fetches:
            await fetch_histories(
                client,
                users,
                rooms,
                args.history_fetches,
                args.history_limit,
                args.concurrency,
                metrics,
            )

        persistence_failures = await verify_persistence(
            client,
            users,
            rooms,
            min(args.persistence_samples, len(rooms)),
            metrics,
        )
        if persistence_failures:
            metrics.errors["persistence"] += persistence_failures

    await close_websockets(sockets)
    metrics.print_summary()
    criteria = collect_criteria(metrics, args)
    print_criteria(criteria)

    if any(not result.passed for result in criteria):
        return 1
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run backend/db pressure scenarios.")
    parser.add_argument("--base-url", default=DEFAULT_ARGS["base_url"])
    parser.add_argument("--ws-url", default=DEFAULT_ARGS["ws_url"])
    parser.add_argument("--prefix", default=DEFAULT_ARGS["prefix"])
    parser.add_argument("--users", type=int, default=DEFAULT_ARGS["users"])
    parser.add_argument("--online-users", type=int, default=DEFAULT_ARGS["online_users"])
    parser.add_argument("--rooms", type=int, default=DEFAULT_ARGS["rooms"])
    parser.add_argument("--room-type", choices=["direct", "group"], default=DEFAULT_ARGS["room_type"])
    parser.add_argument("--group-size", type=int, default=DEFAULT_ARGS["group_size"])
    parser.add_argument("--messages-per-room", type=int, default=DEFAULT_ARGS["messages_per_room"])
    parser.add_argument("--history-fetches", type=int, default=DEFAULT_ARGS["history_fetches"])
    parser.add_argument("--history-limit", type=int, default=DEFAULT_ARGS["history_limit"])
    parser.add_argument("--persistence-samples", type=int, default=DEFAULT_ARGS["persistence_samples"])
    parser.add_argument("--concurrency", type=int, default=DEFAULT_ARGS["concurrency"])
    parser.add_argument("--request-timeout", type=float, default=DEFAULT_ARGS["request_timeout"])
    parser.add_argument("--wait-timeout", type=int, default=DEFAULT_ARGS["wait_timeout"])
    parser.add_argument(
        "--max-p95-ms",
        type=float,
        default=DEFAULT_ARGS["max_p95_ms"],
        help="Backward-compatible alias for --max-send-message-p95-ms.",
    )
    parser.add_argument("--max-register-p95-ms", type=float, default=DEFAULT_ARGS["max_register_p95_ms"])
    parser.add_argument("--max-login-p95-ms", type=float, default=DEFAULT_ARGS["max_login_p95_ms"])
    parser.add_argument("--max-ws-connect-p95-ms", type=float, default=DEFAULT_ARGS["max_ws_connect_p95_ms"])
    parser.add_argument("--max-create-room-p95-ms", type=float, default=DEFAULT_ARGS["max_create_room_p95_ms"])
    parser.add_argument("--max-send-message-p95-ms", type=float, default=DEFAULT_ARGS["max_send_message_p95_ms"])
    parser.add_argument(
        "--max-fetch-messages-p95-ms",
        type=float,
        default=DEFAULT_ARGS["max_fetch_messages_p95_ms"],
    )
    parser.add_argument(
        "--max-verify-persist-p95-ms",
        type=float,
        default=DEFAULT_ARGS["max_verify_persist_p95_ms"],
    )
    parser.add_argument("--max-errors", type=int, default=DEFAULT_ARGS["max_errors"])
    parser.add_argument("--fail-on-errors", action="store_true")
    return parser.parse_args()


def main() -> None:
    raise SystemExit(asyncio.run(run(parse_args())))


if __name__ == "__main__":
    main()
