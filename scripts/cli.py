"""Command-line interface for executing benchmarks and inspecting history records."""

import argparse
import json
import sys
from typing import Optional

from scripts.runner import run_benchmark
from scripts.writer import DEFAULT_HISTORY_FILE, read_records


def handle_run(args: argparse.Namespace) -> int:
    """Execute a benchmark run against an agent."""
    print(f"[Benchmark] Evaluating agent '{args.agent}'...")
    print(f"[Benchmark] User Prompt: {args.prompt}")

    record = run_benchmark(
        agent=args.agent,
        user_prompt=args.prompt,
        command=args.command,
        timeout_seconds=args.timeout,
        upstream_url=args.upstream,
    )

    print(f"\n[Result] Run ID: {record.run_id}")
    print(f"[Result] Status: {record.status.value}")
    print(f"[Result] Exit Code: {record.exit_code}")
    print(f"[Result] Duration: {record.duration_seconds}s")
    print(f"[Result] Start Time: {record.start_time}")
    print(f"[Result] End Time: {record.end_time}")
    print(f"[Result] Tokens: in={record.token_usage.input_tokens}, out={record.token_usage.output_tokens}, total={record.token_usage.total_tokens}")
    print(f"[Result] Output appended to: {DEFAULT_HISTORY_FILE}")

    return 0 if record.status.value == "SUCCESS" else 1


def handle_list(args: argparse.Namespace) -> int:
    """List recorded benchmark runs from the history file."""
    records = read_records()
    if not records:
        print(f"No records found in {DEFAULT_HISTORY_FILE}")
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


def handle_show(args: argparse.Namespace) -> int:
    """Display full details and trajectory of a specific run."""
    records = read_records()
    match = next((r for r in records if r.run_id == args.run_id), None)
    if not match:
        print(f"Record with run_id '{args.run_id}' not found in {DEFAULT_HISTORY_FILE}", file=sys.stderr)
        return 1

    print(json.dumps(match.model_dump(), indent=2))
    return 0


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="agent-benchmark",
        description="Deterministic AI Agent Benchmark Harness",
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # 'run' subcommand
    run_parser = subparsers.add_parser("run", help="Run a benchmark against a target agent")
    run_parser.add_argument("--agent", required=True, help="Agent identifier (e.g. codex, claude, opencode)")
    run_parser.add_argument("--prompt", required=True, help="User prompt to execute")
    run_parser.add_argument("--command", default=None, help="Explicit shell command to execute the agent")
    run_parser.add_argument("--timeout", type=float, default=300.0, help="Execution timeout in seconds")
    run_parser.add_argument("--upstream", default=None, help="Custom upstream LLM API URL for token proxy")
    run_parser.set_defaults(func=handle_run)

    # 'list' subcommand
    list_parser = subparsers.add_parser("list", help="List benchmark runs from history")
    list_parser.add_argument("--limit", type=int, default=20, help="Maximum number of recent records to display")
    list_parser.set_defaults(func=handle_list)

    # 'show' subcommand
    show_parser = subparsers.add_parser("show", help="Show full trajectory of a specific benchmark run")
    show_parser.add_argument("run_id", help="Benchmark run ID")
    show_parser.set_defaults(func=handle_show)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
