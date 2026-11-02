"""Thread-safe and process-safe writer for benchmark JSONL history."""

import fcntl
import json
import os
from pathlib import Path
from typing import List, Optional

from scripts.schemas import BenchmarkRecord

# Root project path resolution
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_HISTORY_FILE = PROJECT_ROOT / "benchmark-historis.jsonl"


def append_record(record: BenchmarkRecord, target_path: Optional[Path] = None) -> Path:
    """
    Append a BenchmarkRecord to the designated benchmark-historis.jsonl file.
    Uses an exclusive file lock (fcntl.flock) to ensure atomic writes across concurrent processes.
    """
    dest_path = target_path or DEFAULT_HISTORY_FILE
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
    source_path = target_path or DEFAULT_HISTORY_FILE
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
