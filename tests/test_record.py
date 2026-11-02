"""Tests for the agent helper record.py CLI."""

import argparse
from pathlib import Path
from unittest.mock import patch

from scripts.record import handle_finish, handle_list, handle_log, handle_start
from scripts.schemas import BenchmarkStatus
from scripts.writer import read_records


def test_start_and_finish_session(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    history_file = tmp_path / "benchmark-historis.jsonl"
    monkeypatch.setenv("BENCHMARK_PROJECT_ROOT", str(tmp_path))

    # 1. Start session
    start_args = argparse.Namespace(
        agent="codex",
        prompt="Build a binary search function",
    )
    res_start = handle_start(start_args)
    assert res_start == 0

    session_files = list((tmp_path / ".benchmark_sessions").glob("*.json"))
    assert len(session_files) == 1
    run_id = session_files[0].stem

    # 2. Finish session
    finish_args = argparse.Namespace(
        run_id=run_id,
        input_tokens=120,
        output_tokens=65,
        total_tokens=185,
        status="SUCCESS",
        output="Binary search implemented with unit tests.",
    )
    res_finish = handle_finish(finish_args)
    assert res_finish == 0

    # Verify session file was cleaned up
    assert not (tmp_path / ".benchmark_sessions" / f"{run_id}.json").exists()

    # Verify record in benchmark-historis.jsonl
    records = read_records(history_file)
    assert len(records) == 1
    assert records[0].run_id == run_id
    assert records[0].agent == "codex"
    assert records[0].user_prompt == "Build a binary search function"
    assert records[0].token_usage.total_tokens == 185
    assert records[0].status == BenchmarkStatus.SUCCESS


def test_direct_log_command(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    history_file = tmp_path / "benchmark-historis.jsonl"
    monkeypatch.setenv("BENCHMARK_PROJECT_ROOT", str(tmp_path))

    log_args = argparse.Namespace(
        agent="claude",
        prompt="Fix database connection leak",
        start_time="2026-11-02T02:00:00Z",
        end_time="2026-11-02T02:00:10Z",
        duration=10.0,
        input_tokens=500,
        output_tokens=150,
        total_tokens=650,
        status="SUCCESS",
        output="Fixed defer pool.Close() in handler",
        run_id="bench_custom_999",
    )

    res = handle_log(log_args)
    assert res == 0

    records = read_records(history_file)
    assert len(records) == 1
    assert records[0].run_id == "bench_custom_999"
    assert records[0].duration_seconds == 10.0
    assert records[0].token_usage.input_tokens == 500
