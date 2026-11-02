"""Thread-safe and process-safe writer for benchmark JSONL history."""

import fcntl
import json
import os
from pathlib import Path
from typing import List, Optional

from scripts.schemas import BenchmarkRecord

def resolve_default_history_file() -> Path:
    """Resolve destination history file to the current project root or explicit env var."""
    env_root = os.environ.get("BENCHMARK_PROJECT_ROOT")
    if env_root:
        return Path(env_root).resolve() / "benchmark-historis.jsonl"
    return Path.cwd().resolve() / "benchmark-historis.jsonl"


DEFAULT_HISTORY_FILE = resolve_default_history_file()


def append_record(record: BenchmarkRecord, target_path: Optional[Path] = None) -> Path:
    """
    Append a BenchmarkRecord to the designated benchmark-historis.jsonl file.
    Uses an exclusive file lock (fcntl.flock) to ensure atomic writes across concurrent processes.
    """
    dest_path = target_path or resolve_default_history_file()
    dest_path.parent.mkdir(parents=True, exist_ok=True)


    json_line = record.model_dump_json() + "\n"

    with open(dest_path, "a", encoding="utf-8") as f:
        # Acquire an exclusive advisory lock before writing
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            f.write(json_line)
            f.flush()
            os.fsync(f.fileno())
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    return dest_path


def read_records(target_path: Optional[Path] = None) -> List[BenchmarkRecord]:
    """
    Read all benchmark records from the JSONL history file.
    Returns an empty list if the file does not exist.
    """
    source_path = target_path or resolve_default_history_file()
    if not source_path.exists():
        return []

    records: List[BenchmarkRecord] = []
    with open(source_path, "r", encoding="utf-8") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_SH)
        try:
            for line in f:
                trimmed = line.strip()
                if trimmed:
                    data = json.loads(trimmed)
                    records.append(BenchmarkRecord.model_validate(data))
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    return records
