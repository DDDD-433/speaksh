from __future__ import annotations

import json
import os
from datetime import datetime

from .notes import ensure_data_dir, history_file
from .types import Suggestion


def record_history(request: str, suggestion: Suggestion) -> None:
    ensure_data_dir()
    entry = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "cwd": os.getcwd(),
        "request": request,
        "command": suggestion.command,
        "risk": suggestion.risk,
        "source": suggestion.source,
    }
    with history_file().open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
