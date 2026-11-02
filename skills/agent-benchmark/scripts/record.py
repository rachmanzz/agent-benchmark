"""Agent helper CLI for managing benchmark sessions and persisting history records."""

import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Ensure package root is in sys.path
_pkg_root = str(Path(__file__).resolve().parent.parent)
if _pkg_root not in sys.path:
    sys.path.insert(0, _pkg_root)

from scripts.schemas import (
    BenchmarkRecord,
    BenchmarkStatus,
    TokenUsage,
    current_utc_iso,
)
from scripts.writer import append_record, read_records, resolve_default_history_file

def get_state_dir() -> Path:
    """Resolve directory for active benchmark sessions dynamically."""
    env_root = os.environ.get("BENCHMARK_PROJECT_ROOT")
    base = Path(env_root).resolve() if env_root else Path.cwd().resolve()
    return base / ".benchmark_sessions"


def handle_start(args: argparse.Namespace) -> int:
    """Initialize a benchmark session, recording start timestamp and user prompt."""
    state_dir = get_state_dir()
    state_dir.mkdir(parents=True, exist_ok=True)
    run_id = f"bench_{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    start_time = current_utc_iso()

    session_data = {
        "run_id": run_id,
        "agent": args.agent,
        "user_prompt": args.prompt,
        "start_time": start_time,
        "start_perf": time.perf_counter(),
    }

    session_file = state_dir / f"{run_id}.json"
    session_file.write_text(json.dumps(session_data, indent=2), encoding="utf-8")

    # Output run_id so the calling agent can capture it
    print(run_id)
    return 0


def handle_finish(args: argparse.Namespace) -> int:
    """Finalize an active session, compute elapsed duration, and persist to benchmark-historis.jsonl."""
    state_dir = get_state_dir()
    session_file = state_dir / f"{args.run_id}.json"
    if not session_file.exists():
        print(f"Error: Active session '{args.run_id}' not found in {state_dir}", file=sys.stderr)
        return 1

    session_data = json.loads(session_file.read_text(encoding="utf-8"))
    end_time = current_utc_iso()
    end_perf = time.perf_counter()

    duration = round(end_perf - session_data.get("start_perf", end_perf), 4)

    in_tok = args.input_tokens or 0
    out_tok = args.output_tokens or 0
    tot_tok = args.total_tokens or (in_tok + out_tok)

    tokens = TokenUsage(
        input_tokens=in_tok,
        output_tokens=out_tok,
        total_tokens=tot_tok,
    )

    status_val = BenchmarkStatus(args.status.upper())

    record = BenchmarkRecord(
        run_id=session_data["run_id"],
        agent=session_data["agent"],
        user_prompt=session_data["user_prompt"],
        start_time=session_data["start_time"],
        end_time=end_time,
        duration_seconds=duration,
        token_usage=tokens,
        trajectory=[],
        exit_code=0 if status_val == BenchmarkStatus.SUCCESS else 1,
        status=status_val,
        final_output=args.output or "",
    )

    history_path = append_record(record)
    session_file.unlink(missing_ok=True)

    # Clean up state dir if empty
    try:
        state_dir.rmdir()
    except OSError:
        pass

    print(f"Benchmark record saved to {history_path}")
    print(f"Duration: {duration}s | Tokens: {tot_tok} (in={in_tok}, out={out_tok})")
    return 0


def handle_log(args: argparse.Namespace) -> int:
    """Record a completed benchmark entry in a single direct command."""
    run_id = args.run_id or f"bench_{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

    # Compute duration from timestamps if duration not explicitly given
    if args.duration is not None:
        duration = args.duration
    else:
        try:
            t_start = datetime.fromisoformat(args.start_time)
            t_end = datetime.fromisoformat(args.end_time)
            duration = round(abs((t_end - t_start).total_seconds()), 4)
        except Exception:
            duration = 0.0

    in_tok = args.input_tokens or 0
    out_tok = args.output_tokens or 0
    tot_tok = args.total_tokens or (in_tok + out_tok)

    tokens = TokenUsage(
        input_tokens=in_tok,
        output_tokens=out_tok,
        total_tokens=tot_tok,
    )

    status_val = BenchmarkStatus(args.status.upper())

    record = BenchmarkRecord(
        run_id=run_id,
        agent=args.agent,
        user_prompt=args.prompt,
        start_time=args.start_time,
        end_time=args.end_time,
        duration_seconds=duration,
        token_usage=tokens,
        trajectory=[],
        exit_code=0 if status_val == BenchmarkStatus.SUCCESS else 1,
        status=status_val,
        final_output=args.output or "",
    )

    history_path = append_record(record)
    print(f"Benchmark record saved to {history_path}")
    return 0


def handle_list(args: argparse.Namespace) -> int:
    """List benchmark entries from benchmark-historis.jsonl."""
    history_file = resolve_default_history_file()
    records = read_records(history_file)
    if not records:
        print(f"No records found in {history_file}")
        return 0

    if args.limit:
        records = records[-args.limit:]

    header = f"{'Run ID':<32} {'Agent':<12} {'Status':<10} {'Duration':<10} {'Tokens (in/out/tot)':<22} {'Start Time'}"
    print(header)
    print("-" * len(header))

    for rec in records:
        tok_str = f"{rec.token_usage.input_tokens}/{rec.token_usage.output_tokens}/{rec.token_usage.total_tokens}"
        print(f"{rec.run_id:<32} {rec.agent:<12} {rec.status.value:<10} {rec.duration_seconds:<10.2f} {tok_str:<22} {rec.start_time}")

    return 0


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="record.py",
        description="Benchmark Session Helper for Agents",
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # 'start'
    p_start = subparsers.add_parser("start", help="Start a new benchmark session")
    p_start.add_argument("--agent", required=True, help="Evaluating agent identifier")
    p_start.add_argument("--prompt", required=True, help="User prompt under evaluation")
    p_start.set_defaults(func=handle_start)

    # 'finish'
    p_finish = subparsers.add_parser("finish", help="Finish an active benchmark session")
    p_finish.add_argument("--run-id", required=True, help="Session run ID returned by start")
    p_finish.add_argument("--input-tokens", type=int, default=0, help="Input/prompt token count")
    p_finish.add_argument("--output-tokens", type=int, default=0, help="Output/completion token count")
    p_finish.add_argument("--total-tokens", type=int, default=0, help="Total token count")
    p_finish.add_argument("--status", default="SUCCESS", choices=["SUCCESS", "FAILURE", "TIMEOUT"])
    p_finish.add_argument("--output", default="", help="Summary or final output of the agent execution")
    p_finish.set_defaults(func=handle_finish)

    # 'log'
    p_log = subparsers.add_parser("log", help="Log a completed benchmark entry directly")
    p_log.add_argument("--agent", required=True, help="Evaluating agent identifier")
    p_log.add_argument("--prompt", required=True, help="User prompt evaluated")
    p_log.add_argument("--start-time", required=True, help="Start timestamp in ISO 8601 UTC")
    p_log.add_argument("--end-time", required=True, help="End timestamp in ISO 8601 UTC")
    p_log.add_argument("--duration", type=float, default=None, help="Execution duration in seconds")
    p_log.add_argument("--input-tokens", type=int, default=0, help="Input token count")
    p_log.add_argument("--output-tokens", type=int, default=0, help="Output token count")
    p_log.add_argument("--total-tokens", type=int, default=0, help="Total token count")
    p_log.add_argument("--status", default="SUCCESS", choices=["SUCCESS", "FAILURE", "TIMEOUT"])
    p_log.add_argument("--output", default="", help="Final output or summary")
    p_log.add_argument("--run-id", default=None, help="Optional custom run ID")
    p_log.set_defaults(func=handle_log)

    # 'list'
    p_list = subparsers.add_parser("list", help="List recorded benchmarks")
    p_list.add_argument("--limit", type=int, default=20, help="Max entries to display")
    p_list.set_defaults(func=handle_list)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
