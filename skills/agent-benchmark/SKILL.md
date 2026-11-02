---
name: agent-benchmark
description: >-
  Benchmark AI coding agents (such as Codex, Claude Code, and OpenCode) with deterministic process-level timing, token usage interception, and trajectory logging into benchmark-historis.jsonl.
---

# Agent Benchmark Skill

This skill provides an automated, deterministic benchmark harness for AI coding agents. It measures exact runtime duration, intercepts network token usage, captures real-time trajectories, and records results into `benchmark-historis.jsonl` at the project root.

## Capabilities

1. **Deterministic Process Timing**: Measures exact OS start and end timestamps (`start_time`, `end_time`) and total duration at the process boundary.
2. **Transparent Token Interception**: Routes agent API traffic through an internal interceptor proxy to capture actual input and output tokens consumed.
3. **Trajectory & Step Logging**: Captures each output line, tool invocation, and error with timestamps.
4. **Root Project JSONL Storage**: Automatically appends each execution record to `benchmark-historis.jsonl`.

## How to Run

Execute the benchmark CLI runner from the project root:

```bash
# General invocation
python3 -m scripts.cli run --agent "<agent-name>" --prompt "<user-prompt>" [--command "<cli-command>"]

# Benchmarking Codex
python3 -m scripts.cli run --agent "codex" --prompt "Implement a binary search algorithm in python" --command "codex exec"

# Benchmarking Claude Code
python3 -m scripts.cli run --agent "claude" --prompt "Refactor error handling in server.py" --command "claude -p"

# Benchmarking OpenCode
python3 -m scripts.cli run --agent "opencode" --prompt "Write unit tests for authentication module" --command "opencode run --prompt"
```

## Viewing Benchmark History

```bash
# List recent benchmark runs
python3 -m scripts.cli list

# Inspect full trajectory of a specific run
python3 -m scripts.cli show <run_id>
```

## File Structure

- `SKILL.md`: Skill entry point and operational manual.
- `scripts/schemas.py`: Pydantic data models for benchmark records, tokens, and trajectories.
- `scripts/proxy.py`: Local HTTP token interceptor proxy.
- `scripts/runner.py`: Execution harness and subprocess orchestrator.
- `scripts/writer.py`: Thread-safe JSONL persistence into `benchmark-historis.jsonl`.
- `scripts/cli.py`: Command-line interface.
