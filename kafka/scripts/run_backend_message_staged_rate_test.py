"""Staged backend message rate test.

This runner separates setup from measured steady-rate stages:

prepare phase:
  register users -> login users -> create rooms

message rate stages:
  send POST /chatrooms/{room_id}/messages at controlled rates for a fixed duration

Use this when estimating the message rate a VM can sustain without growing Kafka
consumer lag or backend latency over time.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx

from run_backend_message_burst_test import (
    DEFAULT_BASE_URL,
    DEFAULT_PERSISTENCE_POLL_SECONDS,
    DEFAULT_PERSISTENCE_WAIT_SECONDS,
    DEFAULT_PREPARE_CONCURRENCY,
    DEFAULT_REQUEST_TIMEOUT,
    DEFAULT_WAIT_TIMEOUT,
    PhaseResult,
    Room,
    User,
    auth_headers,
    create_rooms,
    login_users,
    make_users,
    print_phase,
    raise_for_status,
    register_users,
    summarize_phase,
    verify_persistence,
    wait_for_backend,
)


DEFAULT_STAGE_RATES = "250,500,750,1000"
DEFAULT_STAGE_DURATION_SECONDS = 30
DEFAULT_STAGE_CONCURRENCY = 1000
DEFAULT_STAGE_COOLDOWN_SECONDS = 10


@dataclass
class StageRateResult:
    name: str
    target_rate_per_second: int
    requested_count: int
    completed_count: int
    wall_seconds: float
    achieved_requests_per_second: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    max_ms: float
    errors: int


def parse_rates(raw: str) -> list[int]:
    rates = [int(item.strip()) for item in raw.split(",") if item.strip()]
    if not rates:
        raise argparse.ArgumentTypeError("At least one rate is required.")
    if any(rate <= 0 for rate in rates):
        raise argparse.ArgumentTypeError("Rates must be positive integers.")
    return rates


def summarize_stage_rate(
    name: str,
    target_rate: int,
    requested_count: int,
    timings_ms: list[float],
    wall_seconds: float,
    errors: int,
) -> StageRateResult:
    phase = summarize_phase(name, timings_ms, wall_seconds, errors)
    return StageRateResult(
        name=name,
        target_rate_per_second=target_rate,
        requested_count=requested_count,
        completed_count=phase.count,
        wall_seconds=phase.wall_seconds,
        achieved_requests_per_second=phase.requests_per_second,
        p50_ms=phase.p50_ms,
        p95_ms=phase.p95_ms,
        p99_ms=phase.p99_ms,
        max_ms=phase.max_ms,
        errors=phase.errors,
    )


def print_stage_rate(result: StageRateResult) -> None:
    print(
        f"{result.name:20} target={result.target_rate_per_second:5d}/s "
        f"requested={result.requested_count:5d} completed={result.completed_count:5d} "
        f"rps={result.achieved_requests_per_second:8.2f} "
        f"p50={result.p50_ms:8.2f}ms p95={result.p95_ms:8.2f}ms "
        f"p99={result.p99_ms:8.2f}ms max={result.max_ms:8.2f}ms "
        f"errors={result.errors}"
    )


async def run_message_rate_stage(
    client: httpx.AsyncClient,
    users: list[User],
    rooms: list[Room],
    target_rate: int,
    duration_seconds: int,
    concurrency: int,
    prefix: str,
    stage_index: int,
) -> StageRateResult:
    requested_count = target_rate * duration_seconds
    semaphore = asyncio.Semaphore(concurrency)
    timings_ms: list[float] = []
    errors = 0
    stage_started_at = time.perf_counter()

    async def send_one(message_index: int) -> None:
        nonlocal errors
        scheduled_at = stage_started_at + (message_index / target_rate)
        delay = scheduled_at - time.perf_counter()
        if delay > 0:
            await asyncio.sleep(delay)

        room = rooms[message_index % len(rooms)]
        sender = users[room.sender_index]
        content = (
            f"{prefix} stage={stage_index} rate={target_rate} "
            f"room={room.room_id} msg={message_index} id={uuid.uuid4().hex[:10]}"
        )
        async with semaphore:
            started_at = time.perf_counter()
            try:
                response = await client.post(
                    f"/chatrooms/{room.room_id}/messages",
                    json={"content": content},
                    headers=auth_headers(sender),
                )
                raise_for_status(response, "send_message_rate_stage")
                room.last_message = content
                timings_ms.append((time.perf_counter() - started_at) * 1000)
            except Exception as exc:
                errors += 1
                print(f"send_message error stage={stage_index} msg={message_index}: {exc}")

    tasks = [asyncio.create_task(send_one(index)) for index in range(requested_count)]
    await asyncio.gather(*tasks)
    wall_seconds = time.perf_counter() - stage_started_at

    return summarize_stage_rate(
        f"stage_{stage_index}_{target_rate}rps",
        target_rate,
        requested_count,
        timings_ms,
        wall_seconds,
        errors,
    )


def save_report(
    output_dir: Path,
    args: argparse.Namespace,
    prepare_phases: list[PhaseResult],
    stages: list[StageRateResult],
    persistence_failures: int,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    report_path = output_dir / f"backend-message-staged-rate-report-{timestamp}.json"
    successful_stages = [
        stage
        for stage in stages
        if stage.errors == 0 and stage.completed_count == stage.requested_count
    ]
    max_successful_rate = (
        max(stage.target_rate_per_second for stage in successful_stages)
        if successful_stages
        else 0
    )
    payload = {
        "generatedAtUtc": timestamp,
        "scenario": "backend-message-staged-rate",
        "baseUrl": args.base_url,
        "users": args.users,
        "rooms": args.rooms,
        "roomType": args.room_type,
        "stageRatesPerSecond": parse_rates(args.stage_rates),
        "stageDurationSeconds": args.stage_duration_seconds,
        "stageConcurrency": args.stage_concurrency,
        "prepareConcurrency": args.prepare_concurrency,
        "maxSuccessfulTargetRatePerSecond": max_successful_rate,
        "persistenceFailures": persistence_failures,
        "preparePhases": [asdict(phase) for phase in prepare_phases],
        "stages": [asdict(stage) for stage in stages],
    }
    report_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
    return report_path


def parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(
        description="Run staged steady-rate backend message tests through API -> Kafka -> DB."
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--prefix", default="staged")
    parser.add_argument("--users", type=int, default=1000)
    parser.add_argument("--rooms", type=int)
    parser.add_argument("--room-type", choices=["direct", "group"], default="direct")
    parser.add_argument("--group-size", type=int, default=5)
    parser.add_argument("--stage-rates", default=DEFAULT_STAGE_RATES)
    parser.add_argument("--stage-duration-seconds", type=int, default=DEFAULT_STAGE_DURATION_SECONDS)
    parser.add_argument("--stage-concurrency", type=int, default=DEFAULT_STAGE_CONCURRENCY)
    parser.add_argument("--stage-cooldown-seconds", type=int, default=DEFAULT_STAGE_COOLDOWN_SECONDS)
    parser.add_argument("--prepare-concurrency", type=int, default=DEFAULT_PREPARE_CONCURRENCY)
    parser.add_argument("--persistence-samples", type=int, default=50)
    parser.add_argument("--persistence-wait-seconds", type=float, default=DEFAULT_PERSISTENCE_WAIT_SECONDS)
    parser.add_argument("--persistence-poll-seconds", type=float, default=DEFAULT_PERSISTENCE_POLL_SECONDS)
    parser.add_argument("--request-timeout", type=float, default=DEFAULT_REQUEST_TIMEOUT)
    parser.add_argument("--wait-timeout", type=int, default=DEFAULT_WAIT_TIMEOUT)
    parser.add_argument("--stop-on-error", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=repo_root / "kafka" / "reports")
    return parser.parse_args()


async def run(args: argparse.Namespace) -> int:
    rates = parse_rates(args.stage_rates)
    room_count = args.rooms or args.users
    users = make_users(args.users, args.prefix)
    timeout = httpx.Timeout(args.request_timeout, connect=10.0)

    print("=== Backend Message Staged Rate Test ===")
    print(f"base_url={args.base_url}")
    print(f"users={args.users} rooms={room_count} room_type={args.room_type}")
    print(f"stage_rates={rates}")
    print(f"stage_duration_seconds={args.stage_duration_seconds}")
    print(f"stage_concurrency={args.stage_concurrency}")
    print(f"stage_cooldown_seconds={args.stage_cooldown_seconds}")
    print(f"prepare_concurrency={args.prepare_concurrency}")

    await wait_for_backend(args.base_url, args.wait_timeout)

    prepare_phases: list[PhaseResult] = []
    stages: list[StageRateResult] = []
    persistence_failures = 0

    async with httpx.AsyncClient(base_url=args.base_url, timeout=timeout) as client:
        print("\n=== Prepare Phase ===")
        register = await register_users(client, users, args.prepare_concurrency)
        prepare_phases.append(register)
        print_phase(register)

        login = await login_users(client, users, args.prepare_concurrency)
        prepare_phases.append(login)
        print_phase(login)

        rooms, create_room = await create_rooms(
            client,
            users,
            room_count,
            args.room_type,
            args.group_size,
            args.prepare_concurrency,
        )
        prepare_phases.append(create_room)
        print_phase(create_room)

        print("\n=== Message Rate Stages ===")
        for stage_index, rate in enumerate(rates, start=1):
            result = await run_message_rate_stage(
                client,
                users,
                rooms,
                rate,
                args.stage_duration_seconds,
                args.stage_concurrency,
                args.prefix,
                stage_index,
            )
            stages.append(result)
            print_stage_rate(result)
            if args.stop_on_error and result.errors:
                print("Stopping because --stop-on-error is set and this stage had errors.")
                break
            if args.stage_cooldown_seconds and stage_index < len(rates):
                print(f"cooldown {args.stage_cooldown_seconds}s before next stage...")
                await asyncio.sleep(args.stage_cooldown_seconds)

        if args.persistence_samples:
            print("\n=== Persistence Verification ===")
            persistence_failures, verify = await verify_persistence(
                client,
                users,
                rooms,
                min(args.persistence_samples, len(rooms)),
                args.persistence_wait_seconds,
                args.persistence_poll_seconds,
            )
            print_phase(verify)

    report_path = save_report(args.output_dir, args, prepare_phases, stages, persistence_failures)

    print("\n=== Staged Rate Result ===")
    for stage in stages:
        print(
            f"{stage.name}: target={stage.target_rate_per_second}/s "
            f"achieved={stage.achieved_requests_per_second:.2f}/s "
            f"errors={stage.errors} p95={stage.p95_ms:.2f}ms p99={stage.p99_ms:.2f}ms"
        )
    print(f"persistence_failures={persistence_failures}")
    print(f"report={report_path}")

    return 1 if any(stage.errors for stage in stages) or persistence_failures else 0


def main() -> None:
    raise SystemExit(asyncio.run(run(parse_args())))


if __name__ == "__main__":
    main()
