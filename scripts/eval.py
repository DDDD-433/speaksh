#!/usr/bin/env python3
"""Lightweight local eval harness for speaksh command quality.

Standard library only. Each task runs against a fresh temporary
SPEAKSH_HOME so no state leaks between tasks or into ~/.speaksh.

Usage:
    python scripts/eval.py --no-model   # fallback + safety tasks, no model load
    python scripts/eval.py              # same tasks, model-backed suggestions
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Iterator

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import speaksh  # noqa: E402

DEFAULT_TASKS = ROOT / "eval" / "tasks.jsonl"


@contextlib.contextmanager
def temporary_speaksh_home() -> Iterator[str]:
    previous = os.environ.get("SPEAKSH_HOME")
    with tempfile.TemporaryDirectory(prefix="speaksh-eval-") as td:
        os.environ["SPEAKSH_HOME"] = td
        try:
            yield td
        finally:
            if previous is None:
                os.environ.pop("SPEAKSH_HOME", None)
            else:
                os.environ["SPEAKSH_HOME"] = previous


def load_tasks(path: Path) -> list[dict]:
    tasks = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            tasks.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{path}:{line_no}: invalid JSON: {exc}")
    return tasks


def expected_commands(task: dict) -> list[str]:
    if "expected_commands" in task:
        return list(task["expected_commands"])
    if "expected_command" in task:
        return [task["expected_command"]]
    return []


def command_matches(task: dict, got_command: str | None) -> tuple[bool, str]:
    if got_command is None:
        return False, "command=None"
    commands = expected_commands(task)
    if commands:
        if got_command in commands:
            return True, f"command={got_command!r}"
        return False, f"command={got_command!r} expected_one_of={commands!r}"
    if "match" in task:
        pattern = task["match"]
        if re.search(pattern, got_command):
            return True, f"command={got_command!r} match={pattern!r}"
        return False, f"command={got_command!r} match={pattern!r}"
    raise KeyError("fallback task requires expected_command, expected_commands, or match")


def eval_fallback_task(task: dict, use_model: bool, model_name: str, model_backend: str, adapter_path: str | None) -> tuple[bool, str]:
    with temporary_speaksh_home():
        for note in task.get("notes", []):
            speaksh.add_note(note)
        suggestion = speaksh.suggest_command(
            task["input"],
            use_model=use_model,
            model_name=model_name,
            model_backend=model_backend,
            adapter_path=adapter_path,
        )

    got_command = suggestion.command if suggestion else None
    ok, detail = command_matches(task, got_command)
    if not ok:
        return False, detail

    if "risk" in task:
        got_risk, _ = speaksh.classify_risk(got_command)
        if got_risk != task["risk"]:
            return False, f"risk={got_risk!r} expected={task['risk']!r}"

    return True, f"command={got_command!r}"


def eval_safety_task(task: dict) -> tuple[bool, str]:
    command = task.get("command") or task["input"]
    got_risk, reasons = speaksh.classify_risk(command)
    expected_risk = task["expected_risk"]
    if got_risk != expected_risk:
        return False, f"risk={got_risk!r} expected={expected_risk!r} reasons={reasons}"
    return True, f"risk={got_risk!r}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run speaksh command-quality evals.")
    parser.add_argument("--no-model", action="store_true", help="Use the deterministic fallback instead of the local model.")
    parser.add_argument("--model", default=speaksh.DEFAULT_MODEL_NAME, help=f"Model name/path. Default: {speaksh.DEFAULT_MODEL_NAME}")
    parser.add_argument(
        "--model-backend",
        choices=("mlx", "transformers", "gguf"),
        default=speaksh.DEFAULT_MODEL_BACKEND,
        help=f"Local inference backend. Default: {speaksh.DEFAULT_MODEL_BACKEND}",
    )
    parser.add_argument("--adapter-path", help="Optional local MLX LoRA adapter directory.")
    parser.add_argument("--tasks", type=Path, default=DEFAULT_TASKS, help=f"Path to a JSONL task file. Default: {DEFAULT_TASKS}")
    args = parser.parse_args(argv)
    if args.adapter_path and args.model_backend != "mlx" and not args.no_model:
        parser.error("--adapter-path is only supported with --model-backend mlx")

    tasks = load_tasks(args.tasks)
    use_model = not args.no_model
    model_name = speaksh.effective_model_name(args.model, args.model_backend)

    passed = 0
    failed = 0
    category_totals: dict[str, list[int]] = {}  # category -> [passed, total]
    for index, task in enumerate(tasks, start=1):
        mode = task.get("mode", "fallback")
        if mode == "safety":
            ok, detail = eval_safety_task(task)
        elif mode == "fallback":
            ok, detail = eval_fallback_task(
                task,
                use_model=use_model,
                model_name=model_name,
                model_backend=args.model_backend,
                adapter_path=args.adapter_path,
            )
        else:
            ok, detail = False, f"unknown mode {mode!r}"

        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {index:>2} {mode:<8} {task.get('input', '')!r} ({detail})")
        if ok:
            passed += 1
        else:
            failed += 1

        category = task.get("category")
        if category:
            counts = category_totals.setdefault(category, [0, 0])
            counts[0] += 1 if ok else 0
            counts[1] += 1

    total = passed + failed
    print(f"\ntotal={total} passed={passed} failed={failed}")
    if category_totals:
        print("by_category:")
        for category in sorted(category_totals):
            cat_passed, cat_total = category_totals[category]
            print(f"  {category}: {cat_passed}/{cat_total}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
