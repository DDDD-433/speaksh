from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Note:
    timestamp: str
    cwd: str
    content: str


@dataclass
class Suggestion:
    command: str
    explanation: str
    risk: str = "low"
    source: str = "heuristic"
