# Agent Benchmark

A deterministic, zero-mock benchmark harness for evaluating AI coding agents (such as Codex, Claude Code, OpenCode, and others).

## Features

- **Process-Level Timing**: Tracks real start time (`start_time`), end time (`end_time`), and execution duration (`duration_seconds`) at the OS subprocess level.
- **Deterministic Token Tracking**: Intercepts real token usage (`input_tokens`, `output_tokens`, `total_tokens`) from agent API requests or output streams without relying on agent compliance.
- **Trajectory Capture**: Records timestamped execution steps, tool invocations, and output logs.
- **Atomic JSONL Logging**: Persists benchmark records into `benchmark-historis.jsonl` located at the project root using file locks to prevent concurrency issues.
- **Antigravity Skill Compatible**: Structured as an installable agent skill (`SKILL.md`) that can be mounted into any workspace or global agent environment.

## Usage

### Run from CLI

```bash
# Run benchmark against a target agent CLI command
python -m scripts.cli run --agent "codex" --prompt "Refactor user authentication service" --command "codex exec"
```

### Installation via Skills CLI

Install directly into any agent-enabled project using the `skills` CLI:

```bash
npx skills add rachmanzz/agent-benchmark
```

Or install manually into `.agents/skills/agent-benchmark/` or `~/.gemini/config/skills/agent-benchmark/`.
