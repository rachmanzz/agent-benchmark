"""Tests for atomic JSONL writer and history reader."""

from scripts.schemas import (
    BenchmarkRecord,
    BenchmarkStatus,
    TokenUsage,
    TrajectoryStep,
    current_utc_iso,
)
from scripts.writer import append_record, read_records


def test_append_and_read_records(tmp_path):
    history_file = tmp_path / "benchmark-historis.jsonl"

    record_1 = BenchmarkRecord(
        run_id="run_1",
        agent="claude",
        user_prompt="Task 1",
        start_time=current_utc_iso(),
        end_time=current_utc_iso(),
        duration_seconds=2.0,
        token_usage=TokenUsage(input_tokens=10, output_tokens=20, total_tokens=30),
        trajectory=[],
        exit_code=0,
        status=BenchmarkStatus.SUCCESS,
        final_output="Output 1",
    )

    record_2 = BenchmarkRecord(
        run_id="run_2",
        agent="opencode",
        user_prompt="Task 2",
        start_time=current_utc_iso(),
        end_time=current_utc_iso(),
        duration_seconds=3.5,
        token_usage=TokenUsage(input_tokens=40, output_tokens=50, total_tokens=90),
        trajectory=[
            TrajectoryStep(
                step=1,
                timestamp=current_utc_iso(),
                action="stdout",
                content="Processing...",
                duration_seconds=1.0,
            )
        ],
        exit_code=1,
        status=BenchmarkStatus.FAILURE,
        final_output="Error occurred",
    )

    append_record(record_1, history_file)
    append_record(record_2, history_file)

    loaded = read_records(history_file)
    assert len(loaded) == 2
    assert loaded[0].run_id == "run_1"
    assert loaded[0].agent == "claude"
    assert loaded[0].token_usage.total_tokens == 30

    assert loaded[1].run_id == "run_2"
    assert loaded[1].agent == "opencode"
    assert loaded[1].status == BenchmarkStatus.FAILURE


def test_read_empty_history(tmp_path):
    non_existent = tmp_path / "empty.jsonl"
    records = read_records(non_existent)
    assert records == []
