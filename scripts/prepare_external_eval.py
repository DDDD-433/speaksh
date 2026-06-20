#!/usr/bin/env python3
"""Build a small public-data eval slice from prepared NL-to-shell rows."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import prepare_finetune_data as finetune_data  # noqa: E402

DEFAULT_OUTPUT = ROOT / "eval" / "external_public_tasks.jsonl"

COMMAND_VARIANTS = {
    "ls": ["ls", "ls -la", "ls -al"],
    "ls -a": ["ls -a", "ls -la", "ls -al"],
    "ps": ["ps", "ps aux"],
    "df": ["df", "df -h"],
}

SUPPORTED_EXACT_COMMANDS = {
    "pwd",
    "date",
    "whoami",
    "env",
    "head -n 5 setup_nl2b_fs_1.sh",
    "tail -n 5 setup_nl2b_fs_1.sh",
}


def record_to_eval_task(record: dict[str, Any]) -> dict[str, Any]:
    command = record["command"]
    if record.get("risk") != "low":
        raise ValueError(f"unsupported risk for external eval: {record.get('risk')}")
    if command not in COMMAND_VARIANTS and command not in SUPPORTED_EXACT_COMMANDS:
        raise ValueError(f"unsupported external eval command: {command}")

    task: dict[str, Any] = {
        "input": record["input"],
        "risk": record["risk"],
        "mode": "fallback",
        "category": f"external_{record.get('category', 'other')}",
        "source": record["source"],
        "license": record["license"],
    }
    if command in COMMAND_VARIANTS:
        task["expected_commands"] = COMMAND_VARIANTS[command]
    else:
        task["expected_command"] = command
    return task


def build_external_eval_tasks(records: Iterable[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    seen_inputs: set[str] = set()
    for record in records:
        if record.get("source_split") != "external_test" and record.get("split") != "external_test":
            continue
        try:
            task = record_to_eval_task(record)
        except ValueError:
            continue
        input_key = task["input"].lower()
        if input_key in seen_inputs:
            continue
        seen_inputs.add(input_key)
        tasks.append(task)
        if len(tasks) >= limit:
            break
    return tasks


def write_external_eval_tasks(path: Path, records: Iterable[dict[str, Any]], *, limit: int) -> str:
    tasks = build_external_eval_tasks(records, limit=limit)
    digest = hashlib.sha256()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for task in tasks:
            line = json.dumps(task, sort_keys=True, ensure_ascii=False) + "\n"
            digest.update(line.encode("utf-8"))
            fh.write(line)
    return digest.hexdigest()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare a small external public eval set.")
    parser.add_argument("--config", type=Path, default=finetune_data.DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit-per-source", type=int, default=200)
    parser.add_argument("--max-tasks", type=int, default=12)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--include-disabled", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    splits, _ = finetune_data.prepare_dataset(args)
    tasks = build_external_eval_tasks(splits.get("external_test", []), limit=args.max_tasks)
    if args.dry_run:
        for task in tasks:
            print(json.dumps(task, sort_keys=True, ensure_ascii=False))
        print(f"total={len(tasks)}")
        return 0
    digest = write_external_eval_tasks(args.output, splits.get("external_test", []), limit=args.max_tasks)
    print(f"Wrote {len(tasks)} tasks to {args.output}")
    print(f"sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
