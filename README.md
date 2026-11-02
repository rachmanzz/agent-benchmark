# Agent Benchmark

A deterministic, agent-centric benchmark skill for measuring AI coding agents (such as Codex, Claude Code, OpenCode, and Gemini) with exact process timing, token usage, and trajectory logging into `benchmark-historis.jsonl`.

## How It Works

This repository is designed as an **Agent Skill**:
1. You install the skill into your project using the `skills` CLI.
2. The AI agent reads [`SKILL.md`](./SKILL.md) upon receiving a benchmark prompt from you.
3. The agent autonomously follows the benchmark protocol:
   - Starts a benchmark session via [`scripts/record.py`](./scripts/record.py).
   - Solves the requested programming task.
   - Finalizes the session, writing exact timestamps (`start_time`, `end_time`), elapsed `duration_seconds`, `token_usage`, and the `user_prompt` to `benchmark-historis.jsonl` at your project root.

## Installation

Install directly into any agent-enabled project workspace:

```bash
npx skills add rachmanzz/agent-benchmark
```

Or install manually by cloning or symlinking into:
- Workspace scope: `.agents/skills/agent-benchmark/`
- Global scope: `~/.gemini/config/skills/agent-benchmark/`

## User Workflow

Simply talk to your agent naturally in your workspace:

> "Benchmark solving this issue: implement Dijkstra algorithm in Python with unit tests."

The agent will read the skill instructions, execute the benchmark protocol, and save the verified entry to `benchmark-historis.jsonl`.

## Inspecting History

Inspect benchmark history at any time using the helper CLI:

```bash
# List all recorded benchmark runs
python3 scripts/record.py list

# Or run directly from python module
python3 -m scripts.record list
```
