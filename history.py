"""Persist run history to disk as JSON files in context/history/."""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

HISTORY_DIR = Path("context/history")


def _ensure_dir():
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)


def save_run(label, prompt_id=None):
    """Write a 'running' entry to disk. Returns the run_id (filename stem)."""
    _ensure_dir()
    now = datetime.now(timezone.utc)
    run_id = f"{now.strftime('%Y%m%d-%H%M%S')}_{uuid.uuid4().hex[:8]}"
    entry = {
        "id": run_id,
        "label": label,
        "prompt_id": prompt_id,
        "status": "running",
        "result": None,
        "log": [],
        "started_at": now.isoformat(),
        "finished_at": None,
    }
    (HISTORY_DIR / f"{run_id}.json").write_text(json.dumps(entry, indent=2))
    return run_id


def update_run(run_id, status, result=None, log=None):
    """Update an existing run entry with final state."""
    path = HISTORY_DIR / f"{run_id}.json"
    entry = json.loads(path.read_text())
    entry["status"] = status
    if result is not None:
        entry["result"] = result
    if log is not None:
        entry["log"] = log
    entry["finished_at"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(entry, indent=2))


def list_runs():
    """Read all history entries, newest first."""
    _ensure_dir()
    entries = []
    for path in HISTORY_DIR.glob("*.json"):
        try:
            entries.append(json.loads(path.read_text()))
        except (json.JSONDecodeError, OSError):
            continue
    entries.sort(key=lambda e: e.get("started_at", ""), reverse=True)
    return entries


def get_run(run_id):
    """Read a single run entry by ID. Returns None if not found."""
    path = HISTORY_DIR / f"{run_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def clear_history():
    """Delete all history files. Returns count deleted."""
    _ensure_dir()
    files = list(HISTORY_DIR.glob("*.json"))
    for f in files:
        f.unlink()
    return len(files)
