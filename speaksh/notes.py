from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Sequence

from .types import Note


def data_dir() -> Path:
    """Return the speaksh data directory."""
    return Path(os.environ.get("SPEAKSH_HOME", str(Path.home() / ".speaksh"))).expanduser()


def notes_file() -> Path:
    return data_dir() / "notes.json"


def history_file() -> Path:
    return data_dir() / "history.jsonl"


def ensure_data_dir() -> None:
    data_dir().mkdir(parents=True, exist_ok=True)


def load_notes() -> List[Note]:
    ensure_data_dir()
    path = notes_file()
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return [Note(timestamp=n.get("timestamp", ""), cwd=n.get("cwd", ""), content=n.get("content", "")) for n in raw]


def save_notes(notes: Sequence[Note]) -> None:
    ensure_data_dir()
    payload = [note.__dict__ for note in notes]
    notes_file().write_text(json.dumps(payload, indent=2), encoding="utf-8")


def add_note(content: str, cwd: Optional[str] = None) -> Note:
    note = Note(timestamp=datetime.now().isoformat(timespec="seconds"), cwd=cwd or os.getcwd(), content=content.strip())
    notes = load_notes()
    notes.append(note)
    save_notes(notes)
    return note


def relevant_notes(cwd: Optional[str] = None, limit: int = 8) -> List[Note]:
    cwd = cwd or os.getcwd()
    notes = load_notes()
    exact = [n for n in notes if n.cwd == cwd]
    parent_related = [n for n in notes if n.cwd != cwd and (cwd.startswith(n.cwd) or n.cwd.startswith(cwd))]
    return (exact + parent_related)[-limit:]


def print_notes(notes: Sequence[Note]) -> None:
    if not notes:
        print("No notes yet.")
        return
    grouped: dict[str, List[Note]] = {}
    for note in notes:
        grouped.setdefault(note.cwd, []).append(note)
    for cwd, cwd_notes in grouped.items():
        print(f"\n### Notes for {cwd}:")
        for note in cwd_notes:
            print(f"  - [{note.timestamp}] {note.content}")


def search_notes(query: str) -> List[Note]:
    q = query.lower()
    return [n for n in load_notes() if q in n.content.lower() or q in n.cwd.lower()]
