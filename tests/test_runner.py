"""Tests for the benchmark runner execution harness with real subprocesses."""

import sys
from scripts.runner import run_benchmark
from scripts.schemas import BenchmarkStatus
from scripts.writer import read_records


def test_runner_executes_process_and_records_trajectory(tmp_path):
    history_file = tmp_path / "benchmark-historis.jsonl"
    user_prompt = "Generate a greeting function"

    # Command executes real python process outputting trajectory lines and token metrics
    cmd = [
        sys.executable,
        "-c",
        (
            "import sys, json;\n"
            "print('Starting agent execution');\n"
            "print('def greet(): return \"Hello\"');\n"
            "print(json.dumps({'usage': {'prompt_tokens': 30, 'completion_tokens': 15, 'total_tokens': 45}}));\n"
        ),
    ]

    record = run_benchmark(
        agent="codex",
        user_prompt=user_prompt,
        command=cmd,
        timeout_seconds=10.0,
        target_history_file=history_file,
    )

    assert record.agent == "codex"
    assert record.user_prompt == user_prompt
    assert record.status == BenchmarkStatus.SUCCESS
    assert record.exit_code == 0
    assert record.duration_seconds > 0.0
    assert len(record.trajectory) >= 3

    # Check token parsing from stream
    assert record.token_usage.input_tokens == 30
    assert record.token_usage.output_tokens == 15
    assert record.token_usage.total_tokens == 45

    # Verify history file persistence
    saved = read_records(history_file)
    assert len(saved) == 1
    assert saved[0].run_id == record.run_id
    assert saved[0].user_prompt == user_prompt


def test_runner_handles_timeout(tmp_path):
    history_file = tmp_path / "benchmark-historis.jsonl"
    user_prompt = "Run infinite loop"

    # Subprocess runs sleep exceeding timeout
    cmd = [sys.executable, "-c", "import time; time.sleep(5)"]

    record = run_benchmark(
        agent="claude",
        user_prompt=user_prompt,
        command=cmd,
        timeout_seconds=0.5,
        target_history_file=history_file,
    )

    assert record.status == BenchmarkStatus.TIMEOUT
    assert record.exit_code == -1
    assert any("timed out" in step.content.lower() for step in record.trajectory)
