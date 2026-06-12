from __future__ import annotations

import re
import shlex
import sys
from typing import Optional, Sequence

from .config import DEFAULT_MODEL_BACKEND, DEFAULT_MODEL_NAME
from .model import model_suggestion
from .notes import relevant_notes
from .safety import classify_risk
from .types import Note, Suggestion


def shell_quote_single(value: str) -> str:
    return shlex.quote(value)


def infer_file_extension(text: str) -> Optional[str]:
    extensions = {
        "pdf": "pdf", "png": "png", "jpg": "jpg", "jpeg": "jpeg", "gif": "gif", "webp": "webp",
        "python": "py", "py": "py", "javascript": "js", "js": "js", "typescript": "ts", "ts": "ts",
        "markdown": "md", "md": "md", "text": "txt", "txt": "txt", "video": "mp4", "mp4": "mp4",
    }
    for word, ext in extensions.items():
        if re.search(rf"\b{re.escape(word)}\b", text):
            return ext
    quoted = re.search(r"\.([A-Za-z0-9]{1,8})\b", text)
    if quoted:
        return quoted.group(1)
    return None


def extract_port(text: str) -> Optional[str]:
    match = re.search(r"\bport\s+(\d{2,5})\b|:(\d{2,5})\b", text)
    if match:
        return match.group(1) or match.group(2)
    return None


def extract_size(text: str) -> str:
    match = re.search(r"(\d+)\s*(gb|g|mb|m|kb|k)\b", text)
    if not match:
        return "100M"
    num = match.group(1)
    unit = match.group(2).lower()[0].upper()
    return f"{num}{unit}"


def note_aware_install_command(notes: Sequence[Note]) -> str:
    content = "\n".join(n.content.lower() for n in notes)
    if "pnpm" in content:
        return "pnpm install"
    if "bun" in content:
        return "bun install"
    if "yarn" in content:
        return "yarn install"
    if "pipenv" in content:
        return "pipenv install"
    if "poetry" in content:
        return "poetry install"
    return "npm install"


def heuristic_suggestion(request: str, notes: Sequence[Note]) -> Optional[Suggestion]:
    """Deterministic fallback used when no local model is available."""
    t = request.lower().strip()
    t = re.sub(r"\s+", " ", t)

    command: Optional[str] = None
    explanation = "Generated using built-in fallback rules."

    if any(phrase in t for phrase in ["show hidden", "list hidden", "hidden files", "list files", "show files"]):
        command = "ls -la"
        explanation = "Lists files in the current directory, including hidden files."
    elif any(phrase in t for phrase in ["current directory", "where am i", "working directory", "pwd"]):
        command = "pwd"
        explanation = "Prints the current working directory."
    elif "disk" in t and any(word in t for word in ["usage", "space", "free"]):
        command = "df -h"
        explanation = "Shows disk space usage in human-readable units."
    elif any(word in t for word in ["biggest", "largest", "large files", "bigger than", "larger than"]):
        size = extract_size(t)
        if "bigger than" in t or "larger than" in t or "over" in t:
            command = f"find . -type f -size +{size} -exec ls -lh {{}} \\;"
            explanation = f"Finds files larger than {size} under the current directory."
        else:
            command = "du -ah . | sort -rh | head -20"
            explanation = "Shows the 20 largest files/folders under the current directory."
    elif "find" in t or "search" in t or "locate" in t:
        ext = infer_file_extension(t)
        if ext:
            command = f"find . -type f -iname '*.{ext}'"
            explanation = f"Finds .{ext} files under the current directory."
    elif "port" in t and any(word in t for word in ["using", "listening", "open", "process"]):
        port = extract_port(t) or "3000"
        command = f"lsof -i :{port}"
        explanation = f"Shows processes using port {port}."
    elif any(phrase in t for phrase in ["install dependencies", "install deps", "install packages", "setup dependencies"]):
        command = note_aware_install_command(notes)
        explanation = "Installs project dependencies using the package manager inferred from notes."
    elif any(phrase in t for phrase in ["git status", "status of git", "repo status"]):
        command = "git status"
        explanation = "Shows Git working tree status."
    elif any(phrase in t for phrase in ["compress this folder", "zip this folder", "make a zip"]):
        command = "zip -r archive.zip ."
        explanation = "Creates archive.zip from the current directory."
    elif any(phrase in t for phrase in ["show processes", "list processes", "running processes"]):
        command = "ps aux"
        explanation = "Lists running processes."

    if command is None:
        return None
    risk, _ = classify_risk(command)
    return Suggestion(command=command, explanation=explanation, risk=risk, source="heuristic")


def suggest_command(
    request: str,
    use_model: bool = True,
    model_name: str = DEFAULT_MODEL_NAME,
    model_backend: str = DEFAULT_MODEL_BACKEND,
) -> Optional[Suggestion]:
    notes = relevant_notes()
    if use_model:
        try:
            return model_suggestion(request, notes, model_name, model_backend)
        except Exception as exc:
            print(f"Warning: local model failed: {exc}", file=sys.stderr)
            print("Falling back to built-in rules.", file=sys.stderr)
    return heuristic_suggestion(request, notes)
