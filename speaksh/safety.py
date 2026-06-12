from __future__ import annotations

import re
from typing import List, Tuple


def strip_quoted_text(command: str) -> str:
    """Remove quoted strings before pattern matching to reduce false positives."""
    return re.sub(r"(['\"])(?:\\.|(?!\1).)*\1", "''", command)


def classify_risk(command: str) -> Tuple[str, List[str]]:
    """Classify a shell command with simple conservative heuristics."""
    normalized = strip_quoted_text(command).strip()
    compact = re.sub(r"\s+", " ", normalized)
    reasons: List[str] = []

    hard_block_patterns = [
        (r"(^|[;&|]\s*)(sudo\s+)?rm\s+.*(-r|-R|--recursive).*\s+(/|/\*|~|\$HOME)(\s|$)", "recursive delete of root/home-like path"),
        (r"(^|[;&|]\s*)(sudo\s+)?mkfs(\.|\s|$)", "filesystem formatting command"),
        (r"(^|[;&|]\s*)(sudo\s+)?dd\s+.*\bof=/dev/", "raw disk write with dd"),
        (r"(^|[;&|]\s*)(sudo\s+)?chmod\s+.*(-R|--recursive).*\s+(/|~|\$HOME)(\s|$)", "recursive chmod on broad path"),
        (r"(^|[;&|]\s*)(sudo\s+)?chown\s+.*(-R|--recursive).*\s+(/|~|\$HOME)(\s|$)", "recursive chown on broad path"),
        (r"(^|[;&|]\s*)curl\s+.*\|\s*(sudo\s+)?(bash|sh)", "pipes downloaded code into a shell"),
        (r"(^|[;&|]\s*)wget\s+.*\|\s*(sudo\s+)?(bash|sh)", "pipes downloaded code into a shell"),
        (r":\s*\(\)\s*\{\s*:\s*\|\s*:\s*&\s*}\s*;\s*:", "fork bomb pattern"),
    ]
    warn_patterns = [
        (r"(^|[;&|]\s*)(sudo\s+)?rm\s+", "deletes files"),
        (r"(^|[;&|]\s*)(sudo\s+)?mv\s+", "moves/renames files"),
        (r"(^|[;&|]\s*)(sudo\s+)?chmod\s+", "changes permissions"),
        (r"(^|[;&|]\s*)(sudo\s+)?chown\s+", "changes ownership"),
        (r"(^|[;&|]\s*)(sudo\s+)?kill(all)?\s+", "terminates processes"),
    ]

    for pattern, reason in hard_block_patterns:
        if re.search(pattern, compact):
            reasons.append(reason)
    if reasons:
        return "dangerous", reasons

    for pattern, reason in warn_patterns:
        if re.search(pattern, compact):
            reasons.append(reason)
    if reasons:
        return "medium", reasons

    return "low", []
