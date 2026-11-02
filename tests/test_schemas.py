"""Tests for benchmark data schemas and Pydantic models."""

import pytest
from pydantic import ValidationError

from scripts.schemas import (
    BenchmarkRecord,
    BenchmarkStatus,
    TokenUsage,
    TrajectoryStep,
    current_utc_iso,
)


def test_token_usage_initialization_and_accumulation():
    usage = TokenUsage(input_tokens=100, output_tokens=50, total_tokens=150)
    assert usage.input_tokens == 100
    assert usage.output_tokens == 50
    assert usage.total_tokens == 150

    other = TokenUsage(input_tokens=25, output_tokens=10, total_tokens=35)
    usage.add(other)
    assert usage.input_tokens == 125
    assert usage.output_tokens == 60
    assert usage.total_tokens == 185


def test_trajectory_step_validation():
    step = TrajectoryStep(
        step=1,
        timestamp=current_utc_iso(),
        action="stdout",
        content="Processing task...",
        duration_seconds=0.123,
    )
    assert step.step == 1
    assert step.action == "stdout"
    assert step.duration_seconds == 0.123

    with pytest.raises(ValidationError):
        TrajectoryStep(
            step=0,  # Invalid: step must be >= 1
            timestamp=current_utc_iso(),
            action="stdout",
            content="",
        )


def test_benchmark_record_serialization_roundtrip():
    record = BenchmarkRecord(
        run_id="bench_test_001",
        agent="codex",
        user_prompt="Write a quicksort function in python",
        start_time=current_utc_iso(),
        end_time=current_utc_iso(),
        duration_seconds=1.25,
        token_usage=TokenUsage(input_tokens=50, output_tokens=25, total_tokens=75),
        trajectory=[
            TrajectoryStep(
                step=1,
                timestamp=current_utc_iso(),
                action="stdout",
                content="def quicksort...",
                duration_seconds=1.2,
            )
        ],
        exit_code=0,
        status=BenchmarkStatus.SUCCESS,
        final_output="def quicksort...",
    )

    serialized = record.model_dump_json()
    deserialized = BenchmarkRecord.model_validate_json(serialized)

    assert deserialized.run_id == record.run_id
    assert deserialized.agent == record.agent
    assert deserialized.user_prompt == record.user_prompt
    assert deserialized.token_usage.total_tokens == 75
    assert len(deserialized.trajectory) == 1
    assert deserialized.status == BenchmarkStatus.SUCCESS
