"""End-to-end backend message burst test.

This runner intentionally separates setup from the measured message burst:

prepare phase:
  register users -> login users -> create rooms

message burst phase:
  send one or more messages per room as close together as possible

The measured throughput is only for POST /chatrooms/{room_id}/messages, so it is
easier to compare with Kafka producer/consumer rate and DB write activity.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx


DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_USERS = 1000
DEFAULT_PREPARE_CONCURRENCY = 100
DEFAULT_BURST_CONCURRENCY = 1000
DEFAULT_REQUEST_TIMEOUT = 120.0
DEFAULT_WAIT_TIMEOUT = 60
DEFAULT_PERSISTENCE_WAIT_SECONDS = 30.0
DEFAULT_PERSISTENCE_POLL_SECONDS = 1.0


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
    sender_index: int
    member_indexes: list[int]
    last_message: str | None = None


@dataclass
class PhaseResult:
    name: str
    count: int
    wall_seconds: float
    requests_per_second: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    max_ms: float
    errors: int


def percentile(values: list[float], percentile_value: int) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    index = max(
        0,
        min(
            len(sorted_values) - 1,
            int((percentile_value / 100) * len(sorted_values) + 0.999) - 1,
        ),
    )
    return sorted_values[index]


def summarize_phase(name: str, timings_ms: list[float], wall_seconds: float, errors: int) -> PhaseResult:
    count = len(timings_ms)
    return PhaseResult(
        name=name,
        count=count,
        wall_seconds=wall_seconds,
        requests_per_second=count / wall_seconds if wall_seconds > 0 else 0.0,
        p50_ms=statistics.median(timings_ms) if timings_ms else 0.0,
        p95_ms=percentile(timings_ms, 95),
        p99_ms=percentile(timings_ms, 99),
        max_ms=max(timings_ms) if timings_ms else 0.0,
        errors=errors,
    )


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


def auth_headers(user: User) -> dict[str, str]:
    if not user.token:
        raise RuntimeError(f"User {user.email} has no token")
    return {"Authorization": f"Bearer {user.token}"}


def raise_for_status(response: httpx.Response, label: str) -> None:
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        body = response.text[:1000]
        raise httpx.HTTPStatusError(
            f"{exc} during {label}; response body: {body}",
            request=exc.request,
            response=exc.response,
        ) from exc


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


async def run_limited(items: list[Any], concurrency: int, worker) -> tuple[list[float], int]:
    semaphore = asyncio.Semaphore(concurrency)
    timings_ms: list[float] = []
    errors = 0

    async def run_one(item: Any) -> None:
        nonlocal errors
        async with semaphore:
            start = time.perf_counter()
            try:
                await worker(item)
                timings_ms.append((time.perf_counter() - start) * 1000)
            except Exception:
                errors += 1
                raise

    await asyncio.gather(*(run_one(item) for item in items))
    return timings_ms, errors


async def register_users(
    client: httpx.AsyncClient,
    users: list[User],
    concurrency: int,
) -> PhaseResult:
    async def register(user: User) -> None:
        response = await client.post(
            "/auth/register",
            json={
                "username": user.username,
                "email": user.email,
                "password": user.password,
                "display_name": user.display_name,
            },
        )
        raise_for_status(response, "register")
        user.user_id = response.json()["user_id"]

    start = time.perf_counter()
    timings_ms, errors = await run_limited(users, concurrency, register)
    return summarize_phase("register", timings_ms, time.perf_counter() - start, errors)


async def login_users(
    client: httpx.AsyncClient,
    users: list[User],
    concurrency: int,
) -> PhaseResult:
    async def login(user: User) -> None:
        response = await client.post(
            "/auth/login",
            json={"email": user.email, "password": user.password},
        )
        raise_for_status(response, "login")
        payload = response.json()
        user.token = payload["token"]
        user.user_id = payload["user"]["id"]

    start = time.perf_counter()
    timings_ms, errors = await run_limited(users, concurrency, login)
    return summarize_phase("login", timings_ms, time.perf_counter() - start, errors)


async def create_rooms(
    client: httpx.AsyncClient,
    users: list[User],
    room_count: int,
    room_type: str,
    group_size: int,
    concurrency: int,
) -> tuple[list[Room], PhaseResult]:
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

    rooms: list[Room] = []

    async def create(spec: tuple[int, list[int]]) -> None:
        creator_index, member_indexes = spec
        creator = users[creator_index]
        payload: dict[str, Any] = {
            "room_type": room_type,
            "member_ids": [users[index].user_id for index in member_indexes],
        }
        if room_type == "group":
            payload["name"] = f"Burst Group {uuid.uuid4().hex[:8]}"

        response = await client.post("/chatrooms", json=payload, headers=auth_headers(creator))
        raise_for_status(response, "create_room")
        rooms.append(
            Room(
                room_id=response.json()["id"],
                sender_index=creator_index,
                member_indexes=[creator_index, *member_indexes],
            )
        )

    start = time.perf_counter()
    timings_ms, errors = await run_limited(room_specs, concurrency, create)
    return rooms, summarize_phase("create_room", timings_ms, time.perf_counter() - start, errors)


async def run_message_burst(
    client: httpx.AsyncClient,
    users: list[User],
    rooms: list[Room],
    messages_per_room: int,
    concurrency: int,
    prefix: str,
) -> PhaseResult:
    jobs = [
        (room, message_index)
        for room in rooms
        for message_index in range(messages_per_room)
    ]
    semaphore = asyncio.Semaphore(concurrency)
    start_event = asyncio.Event()
    timings_ms: list[float] = []
    errors = 0

    async def send(job: tuple[Room, int]) -> None:
        nonlocal errors
        room, message_index = job
        sender = users[room.sender_index]
        content = (
            f"{prefix} burst room={room.room_id} msg={message_index} "
            f"id={uuid.uuid4().hex[:10]}"
        )
        await start_event.wait()
        async with semaphore:
            start = time.perf_counter()
            try:
                response = await client.post(
                    f"/chatrooms/{room.room_id}/messages",
                    json={"content": content},
                    headers=auth_headers(sender),
                )
                raise_for_status(response, "send_message")
                room.last_message = content
                timings_ms.append((time.perf_counter() - start) * 1000)
            except Exception:
                errors += 1
                raise

    tasks = [asyncio.create_task(send(job)) for job in jobs]
    await asyncio.sleep(0)
    wall_start = time.perf_counter()
    start_event.set()
    await asyncio.gather(*tasks)
    wall_seconds = time.perf_counter() - wall_start
    return summarize_phase("send_message_burst", timings_ms, wall_seconds, errors)


async def verify_persistence(
    client: httpx.AsyncClient,
    users: list[User],
    rooms: list[Room],
    sample_size: int,
    wait_seconds: float,
    poll_seconds: float,
) -> tuple[int, PhaseResult]:
    sample_rooms = [room for room in rooms if room.last_message][:sample_size]
    timings_ms: list[float] = []
    remaining = {room.room_id: room for room in sample_rooms}

    start_wall = time.perf_counter()
    deadline = start_wall + wait_seconds
    while remaining and time.perf_counter() <= deadline:
        persisted_ids: list[int] = []
        for room_id, room in remaining.items():
            reader = users[room.member_indexes[0]]
            start = time.perf_counter()
            response = await client.get(
                f"/chatrooms/{room.room_id}/messages",
                params={"limit": 200},
                headers=auth_headers(reader),
            )
            raise_for_status(response, "verify_persist")
            timings_ms.append((time.perf_counter() - start) * 1000)
            contents = {message["content"] for message in response.json()["messages"]}
            if room.last_message in contents:
                persisted_ids.append(room_id)

        for room_id in persisted_ids:
            remaining.pop(room_id, None)

        if remaining:
            await asyncio.sleep(poll_seconds)

    failures = len(remaining)

    return failures, summarize_phase(
        "verify_persist",
        timings_ms,
        time.perf_counter() - start_wall,
        failures,
    )


def print_phase(result: PhaseResult) -> None:
    print(
        f"{result.name:20} count={result.count:5d} "
        f"rps={result.requests_per_second:8.2f} "
        f"p50={result.p50_ms:8.2f}ms p95={result.p95_ms:8.2f}ms "
        f"p99={result.p99_ms:8.2f}ms max={result.max_ms:8.2f}ms "
        f"errors={result.errors}"
    )


def save_report(
    output_dir: Path,
    args: argparse.Namespace,
    phases: list[PhaseResult],
    persistence_failures: int,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    report_path = output_dir / f"backend-message-burst-report-{timestamp}.json"
    burst = next(phase for phase in phases if phase.name == "send_message_burst")
    payload = {
        "generatedAtUtc": timestamp,
        "scenario": "backend-message-burst",
        "baseUrl": args.base_url,
        "users": args.users,
        "rooms": args.rooms,
        "roomType": args.room_type,
        "messagesPerRoom": args.messages_per_room,
        "prepareConcurrency": args.prepare_concurrency,
        "burstConcurrency": args.burst_concurrency,
        "sendMessageRequestsPerSecond": burst.requests_per_second,
        "sendMessageCount": burst.count,
        "sendMessageWallSeconds": burst.wall_seconds,
        "persistenceFailures": persistence_failures,
        "phases": [asdict(phase) for phase in phases],
    }
    report_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
    return report_path


def parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(
        description="Run a prepared backend message burst through API -> Kafka -> DB."
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--prefix", default="burst")
    parser.add_argument("--users", type=int, default=DEFAULT_USERS)
    parser.add_argument("--rooms", type=int)
    parser.add_argument("--room-type", choices=["direct", "group"], default="direct")
    parser.add_argument("--group-size", type=int, default=5)
    parser.add_argument("--messages-per-room", type=int, default=1)
    parser.add_argument("--prepare-concurrency", type=int, default=DEFAULT_PREPARE_CONCURRENCY)
    parser.add_argument("--burst-concurrency", type=int, default=DEFAULT_BURST_CONCURRENCY)
    parser.add_argument("--persistence-samples", type=int, default=50)
    parser.add_argument("--persistence-wait-seconds", type=float, default=DEFAULT_PERSISTENCE_WAIT_SECONDS)
    parser.add_argument("--persistence-poll-seconds", type=float, default=DEFAULT_PERSISTENCE_POLL_SECONDS)
    parser.add_argument("--request-timeout", type=float, default=DEFAULT_REQUEST_TIMEOUT)
    parser.add_argument("--wait-timeout", type=int, default=DEFAULT_WAIT_TIMEOUT)
    parser.add_argument("--output-dir", type=Path, default=repo_root / "kafka" / "reports")
    return parser.parse_args()


async def run(args: argparse.Namespace) -> int:
    room_count = args.rooms or args.users
    users = make_users(args.users, args.prefix)
    timeout = httpx.Timeout(args.request_timeout, connect=10.0)

    print("=== Backend Message Burst Test ===")
    print(f"base_url={args.base_url}")
    print(f"users={args.users} rooms={room_count} room_type={args.room_type}")
    print(f"messages_per_room={args.messages_per_room}")
    print(f"prepare_concurrency={args.prepare_concurrency}")
    print(f"burst_concurrency={args.burst_concurrency}")

    await wait_for_backend(args.base_url, args.wait_timeout)

    phases: list[PhaseResult] = []
    async with httpx.AsyncClient(base_url=args.base_url, timeout=timeout) as client:
        print("\n=== Prepare Phase ===")
        register = await register_users(client, users, args.prepare_concurrency)
        phases.append(register)
        print_phase(register)

        login = await login_users(client, users, args.prepare_concurrency)
        phases.append(login)
        print_phase(login)

        rooms, create_room = await create_rooms(
            client,
            users,
            room_count,
            args.room_type,
            args.group_size,
            args.prepare_concurrency,
        )
        phases.append(create_room)
        print_phase(create_room)

        print("\n=== Message Burst Phase ===")
        burst = await run_message_burst(
            client,
            users,
            rooms,
            args.messages_per_room,
            args.burst_concurrency,
            args.prefix,
        )
        phases.append(burst)
        print_phase(burst)

        persistence_failures = 0
        if args.persistence_samples:
            persistence_failures, verify = await verify_persistence(
                client,
                users,
                rooms,
                min(args.persistence_samples, len(rooms)),
                args.persistence_wait_seconds,
                args.persistence_poll_seconds,
            )
            phases.append(verify)
            print_phase(verify)

    report_path = save_report(args.output_dir, args, phases, persistence_failures)

    print("\n=== Burst Result ===")
    print(f"send_message_requests_per_second={burst.requests_per_second:.2f}")
    print(f"send_message_count={burst.count}")
    print(f"send_message_wall_seconds={burst.wall_seconds:.2f}")
    print(f"persistence_failures={persistence_failures}")
    print(f"report={report_path}")

    return 1 if burst.errors or persistence_failures else 0


def main() -> None:
    raise SystemExit(asyncio.run(run(parse_args())))


if __name__ == "__main__":
    main()
