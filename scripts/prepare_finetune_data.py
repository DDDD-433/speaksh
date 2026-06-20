from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import shlex
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from speaksh.safety import classify_risk

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "data" / "sources" / "public_datasets.json"
DEFAULT_OUTPUT = ROOT / "data" / "processed" / "speaksh_public_v1"


def load_source_config(path: Path) -> Dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    if "sources" not in config or not isinstance(config["sources"], list):
        raise ValueError(f"{path} must contain a sources list")
    for source in config["sources"]:
        for key in ("id", "enabled", "license", "adapter"):
            if key not in source:
                raise ValueError(f"source entry missing {key}: {source}")
        if source["license"] not in {"MIT", "Apache-2.0"}:
            raise ValueError(f"unsupported license for {source['id']}: {source['license']}")
    return config


def stable_hash(*parts: str) -> str:
    digest = hashlib.sha256()
    for part in parts:
        digest.update(part.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def first_command_token(command: str) -> str:
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        tokens = command.split()
    while tokens and tokens[0] in {"sudo", "env", "command", "builtin", "time"}:
        tokens = tokens[1:]
    return Path(tokens[0]).name if tokens else ""


def categorize_command(command: str) -> str:
    token = first_command_token(command)
    if token in {"ls", "pwd", "cd", "du", "df", "mkdir", "cp", "mv", "rm", "chmod", "chown", "tar", "zip", "unzip"}:
        return "filesystem"
    if token in {"find", "grep", "rg", "awk", "sed", "sort", "uniq", "head", "tail", "wc"}:
        return "search"
    if token in {"ps", "top", "htop", "kill", "killall", "jobs", "pgrep", "pkill", "lsof"}:
        return "process"
    if token in {"curl", "wget", "ssh", "scp", "rsync", "ping", "nc", "netstat", "ss"}:
        return "network"
    if token in {"npm", "pnpm", "yarn", "bun", "pip", "poetry", "brew", "apt", "apt-get", "dnf", "pacman"}:
        return "package"
    return "other"


def reject_reason(user_input: str, command: str) -> str | None:
    if not user_input.strip() or not command.strip():
        return "empty"
    if "\n" in command or "\r" in command:
        return "multiline"
    if "/testbed" in command:
        return "benchmark_path"
    risk, _ = classify_risk(command)
    if risk == "dangerous":
        return "dangerous"
    return None


def make_record(
    *,
    source_id: str,
    license_name: str,
    user_input: str,
    command: str,
    source_split: str,
    notes: List[str] | None = None,
) -> Dict[str, Any]:
    cleaned_input = re.sub(r"\s+", " ", user_input).strip()
    cleaned_command = re.sub(r"\s+", " ", command).strip()
    risk, _ = classify_risk(cleaned_command)
    return {
        "id": f"{source_id}:{stable_hash(source_id, cleaned_input.lower(), cleaned_command)[:16]}",
        "source": source_id,
        "license": license_name,
        "input": cleaned_input,
        "command": cleaned_command,
        "risk": risk,
        "category": categorize_command(cleaned_command),
        "source_split": source_split,
        "split": "",
        "notes": notes or [],
    }


def extract_pair(source: Dict[str, Any], row: Dict[str, Any]) -> Tuple[str, str] | None:
    adapter = source.get("adapter")
    if adapter == "prompt_completion":
        return str(row.get(source["input_field"], "")), str(row.get(source["command_field"], ""))
    if adapter == "nl_bash":
        return str(row.get("nl", "")), str(row.get("bash", ""))
    if adapter == "messages":
        messages = row.get("messages")
        if not isinstance(messages, list):
            return None
        user = next((msg.get("content", "") for msg in messages if msg.get("role") == "user"), "")
        assistant = next((msg.get("content", "") for msg in messages if msg.get("role") == "assistant"), "")
        return str(user), str(assistant)
    if adapter == "chatml":
        text = str(row.get("text") or row.get("messages") or row.get("prompt") or "")
        user_match = re.search(r"(?:<\|user\|>|<\|im_start\|>user)\s*(.*?)\s*(?:<\|assistant\|>|<\|im_end\|>)", text, flags=re.S)
        assistant_match = re.search(r"(?:<\|assistant\|>|<\|im_start\|>assistant)\s*(.*?)(?:<\||$)", text, flags=re.S)
        if user_match and assistant_match:
            return user_match.group(1), assistant_match.group(1)
        return str(row.get("prompt", "")), str(row.get("completion", ""))
    raise ValueError(f"unknown adapter {adapter!r} for {source['id']}")


def normalize_source_rows(
    source: Dict[str, Any],
    rows: Iterable[Dict[str, Any]],
    *,
    source_split: str = "train",
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    filtered: Counter[str] = Counter()
    seen = 0
    for row in rows:
        seen += 1
        pair = extract_pair(source, row)
        user_input, command = pair if pair else ("", "")
        reason = reject_reason(user_input, command)
        if reason:
            filtered[reason] += 1
            continue
        records.append(
            make_record(
                source_id=source["id"],
                license_name=source["license"],
                user_input=user_input,
                command=command,
                source_split=source_split,
                notes=row.get("notes"),
            )
        )
    return records, {"seen": seen, "kept": len(records), "filtered": dict(filtered)}


def dedupe_and_cap(records: Iterable[Dict[str, Any]], *, max_per_utility: int = 750) -> List[Dict[str, Any]]:
    pair_seen: set[Tuple[str, str]] = set()
    utility_counts: Counter[str] = Counter()
    result: List[Dict[str, Any]] = []
    for record in records:
        key = (record["input"].lower(), record["command"])
        if key in pair_seen:
            continue
        utility = first_command_token(record["command"]) or "other"
        if utility_counts[utility] >= max_per_utility:
            continue
        pair_seen.add(key)
        utility_counts[utility] += 1
        result.append(record)
    return result


def split_records(records: List[Dict[str, Any]], *, seed: int = 42) -> Dict[str, List[Dict[str, Any]]]:
    external = [dict(record, split="external_test") for record in records if record.get("source_split") == "external_test"]
    eligible = [record for record in records if record.get("source_split") != "external_test"]
    shuffled = [dict(record) for record in eligible]
    random.Random(seed).shuffle(shuffled)
    total = len(shuffled)
    if total == 0:
        return {"train": [], "valid": [], "test": [], "external_test": external}
    valid_count = max(1, round(total * 0.05)) if total >= 3 else 0
    test_count = max(1, round(total * 0.05)) if total >= 3 else 0
    train_count = max(0, total - valid_count - test_count)
    train = [dict(record, split="train") for record in shuffled[:train_count]]
    valid = [dict(record, split="valid") for record in shuffled[train_count : train_count + valid_count]]
    test = [dict(record, split="test") for record in shuffled[train_count + valid_count :]]
    return {"train": train, "valid": valid, "test": test, "external_test": external}


def record_to_mlx_message(record: Dict[str, Any]) -> Dict[str, Any]:
    from speaksh.model import build_model_messages
    from speaksh.types import Note
    notes = [Note(timestamp="", cwd="", content=n) for n in record.get("notes", [])]
    messages = build_model_messages(record["input"], notes)
    messages.append({"role": "assistant", "content": record["command"]})
    return {"messages": messages}


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            line = json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n"
            digest.update(line.encode("utf-8"))
            fh.write(line)
    return digest.hexdigest()


def hash_jsonl_rows(rows: Iterable[Dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for row in rows:
        line = json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n"
        digest.update(line.encode("utf-8"))
    return digest.hexdigest()


def artifact_hashes_for_splits(split_records: Dict[str, List[Dict[str, Any]]]) -> Dict[str, str]:
    hashes: Dict[str, str] = {}
    for split_name, rows in split_records.items():
        hashes[f"canonical/{split_name}.jsonl"] = hash_jsonl_rows(rows)
        if split_name != "external_test":
            hashes[f"mlx/{split_name}.jsonl"] = hash_jsonl_rows(record_to_mlx_message(record) for record in rows)
    return hashes


def build_manifest(
    *,
    preset: str,
    source_stats: Dict[str, Dict[str, Any]],
    split_records: Dict[str, List[Dict[str, Any]]],
    artifact_hashes: Dict[str, str] | None = None,
) -> Dict[str, Any]:
    artifact_hashes = artifact_hashes or artifact_hashes_for_splits(split_records)
    return {
        "preset": preset,
        "seed": 42,
        "total_records": sum(len(rows) for rows in split_records.values()),
        "splits": {name: len(rows) for name, rows in split_records.items()},
        "sources": source_stats,
        "artifacts": {
            name: {"sha256": sha}
            for name, sha in sorted(artifact_hashes.items())
        },
    }


def write_outputs(
    output_dir: Path,
    split_records: Dict[str, List[Dict[str, Any]]],
    source_stats: Dict[str, Dict[str, Any]],
    *,
    preset: str = "public-curated-v1",
) -> Dict[str, Any]:
    artifact_hashes: Dict[str, str] = {}
    for split_name, rows in split_records.items():
        artifact = f"canonical/{split_name}.jsonl"
        artifact_hashes[artifact] = write_jsonl(output_dir / artifact, rows)
        if split_name != "external_test":
            mlx_artifact = f"mlx/{split_name}.jsonl"
            artifact_hashes[mlx_artifact] = write_jsonl(
                output_dir / mlx_artifact,
                (record_to_mlx_message(record) for record in rows),
            )
    manifest = build_manifest(
        preset=preset,
        source_stats=source_stats,
        split_records=split_records,
        artifact_hashes=artifact_hashes,
    )
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def load_hf_rows(source: Dict[str, Any], *, limit: int | None) -> List[Dict[str, Any]]:
    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise RuntimeError("Install training dependencies first: pip install -e '.[train]'") from exc

    dataset_kwargs: Dict[str, Any] = {}
    if source.get("dataset_config"):
        dataset_kwargs["name"] = source["dataset_config"]
    split = source.get("hf_split", "train")
    dataset = load_dataset(source["id"], split=split, **dataset_kwargs)
    if limit is not None:
        dataset = dataset.select(range(min(limit, len(dataset))))
    return [dict(row) for row in dataset]


def load_rows_for_source(source: Dict[str, Any], *, limit: int | None) -> List[Dict[str, Any]]:
    if "fixture_rows" in source:
        rows = list(source["fixture_rows"])
        return rows[:limit] if limit is not None else rows
    return load_hf_rows(source, limit=limit)


def merge_stats(base: Dict[str, Any], next_stats: Dict[str, Any]) -> Dict[str, Any]:
    merged = {
        "seen": base.get("seen", 0) + next_stats.get("seen", 0),
        "kept": base.get("kept", 0) + next_stats.get("kept", 0),
        "filtered": dict(base.get("filtered", {})),
    }
    for reason, count in next_stats.get("filtered", {}).items():
        merged["filtered"][reason] = merged["filtered"].get(reason, 0) + count
    return merged


def prepare_dataset(args: argparse.Namespace) -> Tuple[Dict[str, List[Dict[str, Any]]], Dict[str, Dict[str, Any]]]:
    config = load_source_config(Path(args.config))
    all_records: List[Dict[str, Any]] = []
    source_stats: Dict[str, Dict[str, Any]] = {}
    enabled_sources = [
        source
        for source in config["sources"]
        if source.get("enabled") or getattr(args, "include_disabled", False)
    ]
    for source in enabled_sources:
        rows = load_rows_for_source(source, limit=args.limit_per_source)
        records, stats = normalize_source_rows(source, rows, source_split=source.get("destination", "train"))
        source_stats[source["id"]] = merge_stats(source_stats.get(source["id"], {}), stats)
        all_records.extend(records)
        for extra_load in source.get("extra_loads", []):
            extra_source = {**source, **extra_load}
            extra_rows = load_rows_for_source(extra_source, limit=args.limit_per_source)
            extra_records, extra_stats = normalize_source_rows(
                extra_source,
                extra_rows,
                source_split=extra_source.get("destination", "train"),
            )
            source_stats[source["id"]] = merge_stats(source_stats.get(source["id"], {}), extra_stats)
            all_records.extend(extra_records)

    deduped = dedupe_and_cap(all_records, max_per_utility=config.get("max_per_utility", 750))
    grouped = split_records(deduped, seed=args.seed)
    return grouped, source_stats


def run(args: argparse.Namespace) -> int:
    split_records_map, source_stats = prepare_dataset(args)
    manifest = build_manifest(
        preset=args.preset,
        source_stats=source_stats,
        split_records=split_records_map,
    )
    if args.dry_run:
        print(json.dumps(manifest, indent=2, sort_keys=True))
        return 0
    write_outputs(Path(args.output), split_records_map, source_stats, preset=args.preset)
    print(f"Wrote fine-tuning data to {args.output}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare public NL-to-shell data for speaksh fine-tuning.")
    parser.add_argument("--preset", default="public-curated-v1")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit-per-source", type=int, default=None)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--include-disabled", action="store_true")
    return parser


def main() -> int:
    return run(build_parser().parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
