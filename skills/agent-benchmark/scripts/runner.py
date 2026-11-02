"""Subprocess execution harness and benchmark orchestrator for AI coding agents."""

import os
import shlex
import subprocess
import threading
import time
import uuid
from pathlib import Path
from typing import List, Optional, Union

from scripts.proxy import TokenAccumulator, TokenInterceptorProxy, parse_token_payload
from scripts.schemas import (
    BenchmarkRecord,
    BenchmarkStatus,
    TokenUsage,
    TrajectoryStep,
    current_utc_iso,
)
from scripts.writer import append_record


def resolve_default_command(agent: str, user_prompt: str) -> List[str]:
    """Provide standard invocation command patterns for known agents if not explicitly specified."""
    clean_agent = agent.strip().lower()
    if clean_agent in ("codex", "openai-codex"):
        return ["codex", "exec", user_prompt]
    elif clean_agent in ("claude", "claude-code"):
        return ["claude", "-p", user_prompt]
    elif clean_agent in ("opencode",):
        return ["opencode", "run", "--prompt", user_prompt]
    else:
        # Default fallback to executing the agent binary passing the prompt as an argument
        return [agent, user_prompt]


def resolve_upstream_url(agent: str) -> str:
    """Infer the default upstream LLM API target based on agent type."""
    clean_agent = agent.strip().lower()
    if clean_agent in ("claude", "claude-code"):
        return os.environ.get("BENCHMARK_ANTHROPIC_UPSTREAM", "https://api.anthropic.com")
    return os.environ.get("BENCHMARK_OPENAI_UPSTREAM", "https://api.openai.com")


def run_benchmark(
    agent: str,
    user_prompt: str,
    command: Optional[Union[List[str], str]] = None,
    timeout_seconds: float = 300.0,
    working_dir: Optional[Path] = None,
    upstream_url: Optional[str] = None,
    append_to_history: bool = True,
    target_history_file: Optional[Path] = None,
) -> BenchmarkRecord:
    """
    Execute a real benchmark run against a target agent.
    
    1. Starts the local HTTP token interceptor proxy.
    2. Measures exact OS start/end timestamps and execution duration.
    3. Captures real-time output stream trajectory in a non-blocking thread.
    4. Enforces strict process timeouts.
    5. Aggregates token usage from the proxy and process streams.
    6. Appends the finalized BenchmarkRecord to benchmark-historis.jsonl.
    """
    run_id = f"bench_{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    target_upstream = upstream_url or resolve_upstream_url(agent)

    # Format execution command list
    if command is None:
        cmd_args = resolve_default_command(agent, user_prompt)
    elif isinstance(command, str):
        cmd_args = shlex.split(command)
        if user_prompt not in cmd_args and not any(user_prompt in arg for arg in cmd_args):
            cmd_args.append(user_prompt)
    else:
        cmd_args = list(command)
        if user_prompt not in cmd_args and not any(user_prompt in arg for arg in cmd_args):
            cmd_args.append(user_prompt)

    trajectory: List[TrajectoryStep] = []
    stream_accumulator = TokenAccumulator()
    output_buffer: List[str] = []
    trajectory_lock = threading.Lock()

    # Start token interception proxy
    with TokenInterceptorProxy(upstream_url=target_upstream) as proxy:
        env = dict(os.environ)
        # Route agent LLM traffic through interceptor
        env["OPENAI_BASE_URL"] = f"{proxy.base_url}/v1"
        env["ANTHROPIC_BASE_URL"] = proxy.base_url
        env["HTTP_PROXY"] = proxy.base_url
        env["HTTPS_PROXY"] = proxy.base_url

        start_time_iso = current_utc_iso()
        start_perf = time.perf_counter()

        proc = None
        exit_code = -1
        status = BenchmarkStatus.FAILURE

        try:
            proc = subprocess.Popen(
                cmd_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                cwd=str(working_dir) if working_dir else None,
                env=env,
                text=True,
                bufsize=1,
            )

            def _stream_reader() -> None:
                line_start = time.perf_counter()
                for line in iter(proc.stdout.readline, ""):
                    line_dur = time.perf_counter() - line_start
                    line_start = time.perf_counter()
                    output_buffer.append(line)
                    with trajectory_lock:
                        trajectory.append(
                            TrajectoryStep(
                                step=len(trajectory) + 1,
                                timestamp=current_utc_iso(),
                                action="stdout",
                                content=line.rstrip("\r\n"),
                                duration_seconds=round(line_dur, 4),
                            )
                        )
                    parse_token_payload(line, stream_accumulator)

            reader_thread = threading.Thread(target=_stream_reader, daemon=True)
            reader_thread.start()

            # Enforce timeout at process level
            proc.wait(timeout=timeout_seconds)
            reader_thread.join(timeout=2.0)

            exit_code = proc.returncode
            status = BenchmarkStatus.SUCCESS if exit_code == 0 else BenchmarkStatus.FAILURE

        except subprocess.TimeoutExpired:
            if proc:
                proc.kill()
                proc.wait()
            status = BenchmarkStatus.TIMEOUT
            exit_code = -1
            with trajectory_lock:
                trajectory.append(
                    TrajectoryStep(
                        step=len(trajectory) + 1,
                        timestamp=current_utc_iso(),
                        action="error",
                        content=f"Execution timed out after {timeout_seconds} seconds",
                        duration_seconds=0.0,
                    )
                )

        except Exception as exc:
            status = BenchmarkStatus.FAILURE
            with trajectory_lock:
                trajectory.append(
                    TrajectoryStep(
                        step=len(trajectory) + 1,
                        timestamp=current_utc_iso(),
                        action="error",
                        content=f"Subprocess spawn failed: {str(exc)}",
                        duration_seconds=0.0,
                    )
                )

        end_perf = time.perf_counter()
        end_time_iso = current_utc_iso()
        duration_seconds = round(end_perf - start_perf, 4)

        # Reconcile token counts from network proxy and output stream
        proxy_usage = proxy.get_usage()
        stream_usage = stream_accumulator.get_usage()

        final_tokens = TokenUsage(
            input_tokens=proxy_usage.input_tokens or stream_usage.input_tokens,
            output_tokens=proxy_usage.output_tokens or stream_usage.output_tokens,
            total_tokens=proxy_usage.total_tokens or stream_usage.total_tokens,
        )

        final_output_str = "".join(output_buffer).strip()

        record = BenchmarkRecord(
            run_id=run_id,
            agent=agent,
            user_prompt=user_prompt,
            start_time=start_time_iso,
            end_time=end_time_iso,
            duration_seconds=duration_seconds,
            token_usage=final_tokens,
            trajectory=trajectory,
            exit_code=exit_code,
            status=status,
            final_output=final_output_str,
        )

        if append_to_history:
            append_record(record, target_history_file)

        return record
