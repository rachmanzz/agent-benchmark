---
name: agent-benchmark
description: >-
  Use this skill whenever the user asks to benchmark, evaluate, or track performance metrics (start/end timestamps, duration, token usage, user prompt) of executing any task into benchmark-historis.jsonl.
---

# Agent Benchmark Protocol

This skill instructs the agent on how to benchmark tasks and record execution metrics (start time, end time, duration, token usage, and user prompt) into `benchmark-historis.jsonl` located at the project root.

## When to Use

Activate this skill whenever:
- The user asks to benchmark a task (e.g. "benchmark this refactoring", "measure performance of solving this issue", "benchmark implementing X").
- The user requests tracking execution duration, token metrics, or saving benchmark history.

## Execution Protocol

Follow these 3 steps deterministically:

### Step 1: Start Benchmark Session
Before beginning work on the user's task, initialize the benchmark session via the helper script to lock in the exact start timestamp and prompt:

```bash
RUN_ID=$(python3 scripts/record.py start --agent "<your-agent-name>" --prompt "<exact user prompt>")
```
*(Replace `<your-agent-name>` with your identifier, e.g. `codex`, `claude`, `opencode`, `gemini`, etc.)*

### Step 2: Perform the User's Requested Task
Execute the requested coding, debugging, refactoring, or testing work as required by the user.

### Step 3: Finalize and Persist Benchmark Record
Immediately upon completing the task, finalize the benchmark session. Provide token counts (input/output) from your session context or tool metadata:

```bash
python3 scripts/record.py finish \
  --run-id "$RUN_ID" \
  --input-tokens <input_tokens_count> \
  --output-tokens <output_tokens_count> \
  --status "SUCCESS" \
  --output "<brief summary of what was accomplished>"
```
*(If the task encountered an unrecoverable failure, pass `--status "FAILURE"`).*

### Alternative: Direct Single-Command Logging
If both start and end timestamps are already known from your runtime context, log directly in one command:

```bash
python3 scripts/record.py log \
  --agent "<your-agent-name>" \
  --prompt "<exact user prompt>" \
  --start-time "<iso-8601-start-time>" \
  --end-time "<iso-8601-end-time>" \
  --input-tokens <input_tokens> \
  --output-tokens <output_tokens> \
  --status "SUCCESS" \
  --output "<brief summary>"
```

## Storage Location

All records are written append-only to:
`benchmark-historis.jsonl` at the root of the project workspace.
