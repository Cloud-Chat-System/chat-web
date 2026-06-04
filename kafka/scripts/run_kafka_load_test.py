"""Kafka staged load-test runner based on the broker's built-in perf tool."""

from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


SUMMARY_PATTERN = re.compile(
    r"(?P<records>[\d.,]+)\s+records sent,\s+"
    r"(?P<records_per_sec>[\d.,]+)\s+records/sec\s+\((?P<mb_per_sec>[\d.,]+)\s+MB/sec\),\s+"
    r"(?P<avg_latency_ms>[\d.,]+)\s+ms avg latency,\s+"
    r"(?P<max_latency_ms>[\d.,]+)\s+ms max latency,\s+"
    r"(?P<p50_latency_ms>[\d.,]+)\s+ms 50th,\s+"
    r"(?P<p95_latency_ms>[\d.,]+)\s+ms 95th,\s+"
    r"(?P<p99_latency_ms>[\d.,]+)\s+ms 99th"
)


DEFAULT_PROFILE = {
    "scenarioName": "steady-state-throughput-and-online-users",
    "topic": "chat.events",
    "partitions": 12,
    "replicationFactor": 1,
    "messageSizeBytes": 512,
    "stageDurationSeconds": 60,
    "stageRatesPerSecond": [100, 250, 500, 750, 1000],
    "targetMessageRatePerSecond": 1000,
    "targetConcurrentOnlineUsers": 100000,
    "observedOnlineUsersPerVm": 0,
    "producerCount": 1,
    "bootstrapServer": "kafka:9092",
    "acks": "1",
    "compressionType": "none",
    "batchSize": 32768,
    "lingerMs": 5,
    "throughputPassRatio": 0.9,
    "safetyFactor": 0.7,
    "notes": [],
}


@dataclass
class StageResult:
    stage_index: int
    target_rate: int
    duration_seconds: int
    requested_records: int
    produced_records: float | None
    achieved_records_per_sec: float | None
    throughput_ratio: float | None
    avg_latency_ms: float | None
    p95_latency_ms: float | None
    p99_latency_ms: float | None
    max_latency_ms: float | None
    passed: bool
    stdout: str
    stderr: str


def read_profile(path: Path) -> dict[str, Any]:
    profile = json.loads(path.read_text(encoding="utf-8"))
    merged = {**DEFAULT_PROFILE, **profile}
    merged["stageRatesPerSecond"] = profile.get(
        "stageRatesPerSecond",
        DEFAULT_PROFILE["stageRatesPerSecond"],
    )
    merged["notes"] = profile.get("notes", DEFAULT_PROFILE["notes"])
    return merged


def parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[2]
    default_profile = repo_root / "kafka" / "load-profile.example.json"
    default_compose = repo_root / "kafka" / "docker-compose.yml"
    default_output = repo_root / "kafka" / "reports"

    parser = argparse.ArgumentParser(
        description="Run staged Kafka producer load tests via kafka-producer-perf-test.sh."
    )
    parser.add_argument("--profile", type=Path, default=default_profile)
    parser.add_argument("--compose-file", type=Path, default=default_compose)
    parser.add_argument("--output-dir", type=Path, default=default_output)
    parser.add_argument("--rates", help="Comma-separated stage rates that override the profile.")
    parser.add_argument("--stage-duration-seconds", type=int)
    parser.add_argument("--target-rate", type=int)
    parser.add_argument("--target-online-users", type=int)
    parser.add_argument("--observed-online-users-per-vm", type=int)
    parser.add_argument("--producer-count", type=int)
    parser.add_argument("--throughput-pass-ratio", type=float)
    parser.add_argument("--safety-factor", type=float)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def parse_rates(raw: str | None, profile: dict[str, Any]) -> list[int]:
    if raw:
        return [int(item.strip()) for item in raw.split(",") if item.strip()]
    return [int(rate) for rate in profile["stageRatesPerSecond"]]


def run_command(command: list[str], dry_run: bool) -> subprocess.CompletedProcess[str]:
    print(f"$ {' '.join(command)}")
    if dry_run:
        return subprocess.CompletedProcess(command, 0, "", "")
    return subprocess.run(command, capture_output=True, text=True, check=False)


def ensure_topic(compose_file: Path, profile: dict[str, Any], dry_run: bool) -> None:
    command = [
        "docker",
        "compose",
        "-f",
        str(compose_file),
        "exec",
        "-T",
        "kafka",
        "kafka-topics.sh",
        "--bootstrap-server",
        str(profile["bootstrapServer"]),
        "--create",
        "--if-not-exists",
        "--topic",
        str(profile["topic"]),
        "--partitions",
        str(profile["partitions"]),
        "--replication-factor",
        str(profile["replicationFactor"]),
    ]
    completed = run_command(command, dry_run)
    if completed.returncode != 0:
        raise RuntimeError(
            "Failed to create or validate the Kafka topic.\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )


def parse_summary(output: str) -> dict[str, float] | None:
    matches = list(SUMMARY_PATTERN.finditer(output))
    if not matches:
        return None
    match = matches[-1]
    return {
        key: float(value.replace(",", ""))
        for key, value in match.groupdict().items()
    }


def run_stage(
    compose_file: Path,
    profile: dict[str, Any],
    stage_index: int,
    rate: int,
    duration_seconds: int,
    producer_count: int,
    throughput_pass_ratio: float,
    dry_run: bool,
) -> StageResult:
    requested_records = rate * duration_seconds
    client_id = f"{profile['scenarioName']}-stage-{stage_index}"
    command = [
        "docker",
        "compose",
        "-f",
        str(compose_file),
        "exec",
        "-T",
        "kafka",
        "kafka-producer-perf-test.sh",
        "--topic",
        str(profile["topic"]),
        "--num-records",
        str(requested_records),
        "--record-size",
        str(profile["messageSizeBytes"]),
        "--throughput",
        str(rate),
        "--producer-props",
        f"bootstrap.servers={profile['bootstrapServer']}",
        f"acks={profile['acks']}",
        f"compression.type={profile['compressionType']}",
        f"batch.size={profile['batchSize']}",
        f"linger.ms={profile['lingerMs']}",
        f"client.id={client_id}",
    ]
    completed = run_command(command, dry_run)
    if dry_run:
        return StageResult(
            stage_index=stage_index,
            target_rate=rate,
            duration_seconds=duration_seconds,
            requested_records=requested_records,
            produced_records=float(requested_records),
            achieved_records_per_sec=float(rate),
            throughput_ratio=1.0,
            avg_latency_ms=0.0,
            p95_latency_ms=0.0,
            p99_latency_ms=0.0,
            max_latency_ms=0.0,
            passed=True,
            stdout="dry-run",
            stderr="",
        )
    if completed.returncode != 0:
        return StageResult(
            stage_index=stage_index,
            target_rate=rate,
            duration_seconds=duration_seconds,
            requested_records=requested_records,
            produced_records=None,
            achieved_records_per_sec=None,
            throughput_ratio=None,
            avg_latency_ms=None,
            p95_latency_ms=None,
            p99_latency_ms=None,
            max_latency_ms=None,
            passed=False,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )

    metrics = parse_summary(completed.stdout)
    if metrics is None:
        return StageResult(
            stage_index=stage_index,
            target_rate=rate,
            duration_seconds=duration_seconds,
            requested_records=requested_records,
            produced_records=None,
            achieved_records_per_sec=None,
            throughput_ratio=None,
            avg_latency_ms=None,
            p95_latency_ms=None,
            p99_latency_ms=None,
            max_latency_ms=None,
            passed=False,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )

    throughput_ratio = metrics["records_per_sec"] / rate if rate else 0.0
    return StageResult(
        stage_index=stage_index,
        target_rate=rate,
        duration_seconds=duration_seconds,
        requested_records=requested_records,
        produced_records=metrics["records"],
        achieved_records_per_sec=metrics["records_per_sec"],
        throughput_ratio=throughput_ratio,
        avg_latency_ms=metrics["avg_latency_ms"],
        p95_latency_ms=metrics["p95_latency_ms"],
        p99_latency_ms=metrics["p99_latency_ms"],
        max_latency_ms=metrics["max_latency_ms"],
        passed=throughput_ratio >= throughput_pass_ratio,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def estimate_vm_count(
    effective_rate_per_vm: float,
    target_rate: int,
    safety_factor: float,
) -> int | None:
    if effective_rate_per_vm <= 0 or safety_factor <= 0:
        return None
    safe_rate = effective_rate_per_vm * safety_factor
    if safe_rate <= 0:
        return None
    return math.ceil(target_rate / safe_rate)


def print_stage_summary(results: list[StageResult]) -> None:
    print("\n=== Kafka Load Test Summary ===")
    print(
        "stage  target msg/s  actual msg/s  pass%   avg ms   p95 ms   p99 ms   max ms  status"
    )
    for result in results:
        actual = (
            f"{result.achieved_records_per_sec:11.2f}"
            if result.achieved_records_per_sec is not None
            else f"{'-':>11}"
        )
        ratio = (
            f"{result.throughput_ratio * 100:6.1f}"
            if result.throughput_ratio is not None
            else f"{'-':>6}"
        )
        avg = f"{result.avg_latency_ms:7.2f}" if result.avg_latency_ms is not None else f"{'-':>7}"
        p95 = f"{result.p95_latency_ms:7.2f}" if result.p95_latency_ms is not None else f"{'-':>7}"
        p99 = f"{result.p99_latency_ms:7.2f}" if result.p99_latency_ms is not None else f"{'-':>7}"
        max_ms = f"{result.max_latency_ms:7.2f}" if result.max_latency_ms is not None else f"{'-':>7}"
        status = "PASS" if result.passed else "FAIL"
        print(
            f"{result.stage_index:>5} {result.target_rate:>13} {actual} {ratio}%"
            f" {avg} {p95} {p99} {max_ms}  {status}"
        )


def save_report(
    output_dir: Path,
    profile: dict[str, Any],
    results: list[StageResult],
    target_rate: int,
    target_online_users: int,
    observed_online_users_per_vm: int,
    safety_factor: float,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    report_path = output_dir / f"kafka-load-report-{timestamp}.json"
    successful = [result for result in results if result.passed and result.achieved_records_per_sec]
    max_sustainable_rate = max(
        (result.achieved_records_per_sec or 0.0) for result in successful
    ) if successful else 0.0
    payload = {
        "generatedAtUtc": timestamp,
        "profile": profile,
        "targetRatePerSecond": target_rate,
        "targetOnlineUsers": target_online_users,
        "observedOnlineUsersPerVm": observed_online_users_per_vm,
        "safetyFactor": safety_factor,
        "maxSustainableRatePerSecond": max_sustainable_rate,
        "estimatedKafkaVmCount": estimate_vm_count(max_sustainable_rate, target_rate, safety_factor),
        "estimatedAppVmCountForOnlineUsers": (
            math.ceil(target_online_users / observed_online_users_per_vm)
            if observed_online_users_per_vm > 0
            else None
        ),
        "stages": [asdict(result) for result in results],
    }
    report_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
    return report_path


def main() -> int:
    args = parse_args()
    profile = read_profile(args.profile)
    rates = parse_rates(args.rates, profile)
    duration_seconds = args.stage_duration_seconds or int(profile["stageDurationSeconds"])
    target_rate = args.target_rate or int(profile["targetMessageRatePerSecond"])
    target_online_users = args.target_online_users or int(profile["targetConcurrentOnlineUsers"])
    observed_online_users_per_vm = (
        args.observed_online_users_per_vm
        if args.observed_online_users_per_vm is not None
        else int(profile.get("observedOnlineUsersPerVm", 0))
    )
    producer_count = args.producer_count or int(profile["producerCount"])
    throughput_pass_ratio = args.throughput_pass_ratio or float(profile["throughputPassRatio"])
    safety_factor = args.safety_factor or float(profile["safetyFactor"])

    print("=== Kafka Load Profile ===")
    print(f"scenario={profile['scenarioName']}")
    print(f"topic={profile['topic']} partitions={profile['partitions']}")
    print(f"stage_rates={rates}")
    print(f"stage_duration_seconds={duration_seconds}")
    print(f"target_rate_per_second={target_rate}")
    print(f"target_online_users={target_online_users}")
    print(f"producer_count={producer_count}")
    print(f"throughput_pass_ratio={throughput_pass_ratio:.2f}")
    print(f"safety_factor={safety_factor:.2f}")

    ensure_topic(args.compose_file, profile, args.dry_run)

    results: list[StageResult] = []
    for stage_index, rate in enumerate(rates, start=1):
        print(f"\n--- Stage {stage_index}: target {rate} msg/s for {duration_seconds}s ---")
        result = run_stage(
            args.compose_file,
            profile,
            stage_index,
            rate,
            duration_seconds,
            producer_count,
            throughput_pass_ratio,
            args.dry_run,
        )
        results.append(result)
        if result.achieved_records_per_sec is None:
            print("Unable to parse producer output; see report JSON for raw logs.")
            break
        print(
            f"actual={result.achieved_records_per_sec:.2f} msg/s "
            f"p95={result.p95_latency_ms:.2f} ms "
            f"ratio={result.throughput_ratio * 100:.1f}% "
            f"status={'PASS' if result.passed else 'FAIL'}"
        )
        if not result.passed:
            print("Stage failed the throughput threshold; stopping ramp-up here.")
            break

    print_stage_summary(results)
    report_path = save_report(
        args.output_dir,
        profile,
        results,
        target_rate,
        target_online_users,
        observed_online_users_per_vm,
        safety_factor,
    )

    successful = [result for result in results if result.passed and result.achieved_records_per_sec]
    max_sustainable_rate = max(
        (result.achieved_records_per_sec or 0.0) for result in successful
    ) if successful else 0.0
    kafka_vm_count = estimate_vm_count(max_sustainable_rate, target_rate, safety_factor)
    online_vm_count = (
        math.ceil(target_online_users / observed_online_users_per_vm)
        if observed_online_users_per_vm > 0
        else None
    )

    print("\n=== Capacity Estimate ===")
    print(f"max_sustainable_rate_per_vm={max_sustainable_rate:.2f} msg/s")
    if kafka_vm_count is None:
        print("estimated_kafka_vm_count=unavailable")
    else:
        print(f"estimated_kafka_vm_count={kafka_vm_count}")
    if online_vm_count is None:
        print("estimated_app_vm_count_for_online_users=provide observedOnlineUsersPerVm to calculate")
    else:
        print(f"estimated_app_vm_count_for_online_users={online_vm_count}")
    print(f"report={report_path}")

    return 0 if results else 1


if __name__ == "__main__":
    raise SystemExit(main())
