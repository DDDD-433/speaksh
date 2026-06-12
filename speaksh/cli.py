from __future__ import annotations

import argparse
import sys
from typing import Optional, Sequence

from .config import DEFAULT_MODEL_BACKEND, DEFAULT_MODEL_NAME, effective_model_name
from .history import record_history
from .notes import add_note, load_notes, print_notes, search_notes
from .runner import run_command
from .safety import classify_risk
from .suggestions import suggest_command


def handle_request(
    request: str,
    *,
    use_model: bool,
    model_name: str,
    model_backend: str,
    dry_run: bool,
    yes: bool,
    unsafe: bool,
    explain: bool,
) -> int:
    suggestion = suggest_command(request, use_model=use_model, model_name=model_name, model_backend=model_backend)
    if suggestion is None:
        print("No command suggestion available for that request in fallback mode.")
        print("Install/cache the local model, or run with --no-model and phrase it more specifically.")
        return 2

    risk, reasons = classify_risk(suggestion.command)
    suggestion.risk = risk
    record_history(request, suggestion)

    print(f"Suggested command: {suggestion.command}")
    print(f"Risk: {risk}")
    if reasons:
        print("Reasons: " + "; ".join(reasons))
    if explain:
        print(f"Explanation: {suggestion.explanation}")

    if dry_run:
        return 0

    if risk == "dangerous" and not unsafe:
        print("Blocked: dangerous command. Re-run with --unsafe only if you fully understand it.")
        return 3

    if not yes:
        answer = input("Run this command? [y/N] ").strip().lower()
        if answer != "y":
            print("Cancelled.")
            return 0

    return run_command(suggestion.command)


def interactive_loop(*, use_model: bool, model_name: str, model_backend: str) -> int:
    print("speaksh interactive mode")
    print("Type a request, or: note add <text> | note list | note search <query> | exit")
    while True:
        try:
            line = input("speaksh> ").strip()
        except EOFError:
            print()
            return 0
        if not line:
            continue
        if line.lower() in {"exit", "quit", ":q"}:
            return 0
        if line.startswith("note "):
            parts = line.split(maxsplit=2)
            if len(parts) >= 3 and parts[1] == "add":
                add_note(parts[2])
                print("Note added.")
            elif len(parts) == 2 and parts[1] == "list":
                print_notes(load_notes())
            elif len(parts) >= 3 and parts[1] == "search":
                print_notes(search_notes(parts[2]))
            else:
                print("Usage: note add <text> | note list | note search <query>")
            continue
        handle_request(
            line,
            use_model=use_model,
            model_name=model_name,
            model_backend=model_backend,
            dry_run=False,
            yes=False,
            unsafe=False,
            explain=True,
        )


def build_main_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="speaksh",
        description="Local-first natural-language shell companion for Unix/Linux systems.",
    )
    parser.add_argument("--use-model", action="store_true", help="Use the local model backend. This is the default; kept for explicitness.")
    parser.add_argument("--no-model", action="store_true", help="Skip model loading and use deterministic fallback rules only.")
    parser.add_argument("--model", default=DEFAULT_MODEL_NAME, help=f"Model name/path. Default: {DEFAULT_MODEL_NAME}")
    parser.add_argument(
        "--model-backend",
        choices=("mlx", "transformers", "gguf"),
        default=DEFAULT_MODEL_BACKEND,
        help=f"Local inference backend. Default: {DEFAULT_MODEL_BACKEND}",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print the suggested command but do not prompt or run it.")
    parser.add_argument("-y", "--yes", action="store_true", help="Run without asking for confirmation. Use carefully.")
    parser.add_argument("--unsafe", action="store_true", help="Allow dangerous commands that would otherwise be blocked.")
    parser.add_argument("--explain", action="store_true", help="Show a short explanation of the suggested command.")
    parser.add_argument("request", nargs="*", help="Natural language request, e.g. 'show hidden files'.")
    return parser


def handle_note_command(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(prog="speaksh note", description="Manage local speaksh notes.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    add = sub.add_parser("add", help="Add a note for the current directory.")
    add.add_argument("content", nargs="+", help="Note text.")
    sub.add_parser("list", help="List all notes.")
    search = sub.add_parser("search", help="Search notes.")
    search.add_argument("query", help="Search query.")
    args = parser.parse_args(list(argv))

    if args.cmd == "add":
        add_note(" ".join(args.content))
        print("Note added.")
        return 0
    if args.cmd == "list":
        print_notes(load_notes())
        return 0
    if args.cmd == "search":
        print_notes(search_notes(args.query))
        return 0
    return 1


def main(argv: Optional[Sequence[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    if argv and argv[0] == "note":
        return handle_note_command(argv[1:])

    parser = build_main_parser()
    args = parser.parse_args(argv)
    model_name = effective_model_name(args.model, args.model_backend)

    if not args.request:
        return interactive_loop(use_model=not args.no_model, model_name=model_name, model_backend=args.model_backend)

    request = " ".join(args.request)
    return handle_request(
        request,
        use_model=not args.no_model,
        model_name=model_name,
        model_backend=args.model_backend,
        dry_run=args.dry_run,
        yes=args.yes,
        unsafe=args.unsafe,
        explain=args.explain,
    )


if __name__ == "__main__":
    raise SystemExit(main())
