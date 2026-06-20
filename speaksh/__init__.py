from __future__ import annotations

from .cli import build_main_parser, handle_doctor_command, handle_eval_command, handle_note_command, handle_request, interactive_loop, main
from .config import DEFAULT_MODEL_BACKEND, DEFAULT_MODEL_NAME, DEFAULT_TRANSFORMERS_MODEL_NAME, effective_model_name
from .history import record_history
from .model import build_model_messages, command_from_generated_text, model_suggestion
from .notes import add_note, data_dir, ensure_data_dir, history_file, load_notes, notes_file, print_notes, relevant_notes, save_notes, search_notes
from .runner import run_command
from .safety import classify_risk, strip_quoted_text
from .suggestions import heuristic_suggestion, suggest_command
from .types import Note, Suggestion

__version__ = "0.1.0"

__all__ = [
    "DEFAULT_MODEL_BACKEND",
    "DEFAULT_MODEL_NAME",
    "DEFAULT_TRANSFORMERS_MODEL_NAME",
    "Note",
    "Suggestion",
    "__version__",
    "add_note",
    "build_main_parser",
    "build_model_messages",
    "classify_risk",
    "command_from_generated_text",
    "data_dir",
    "effective_model_name",
    "ensure_data_dir",
    "handle_doctor_command",
    "handle_eval_command",
    "handle_note_command",
    "handle_request",
    "heuristic_suggestion",
    "history_file",
    "interactive_loop",
    "load_notes",
    "main",
    "model_suggestion",
    "notes_file",
    "print_notes",
    "record_history",
    "relevant_notes",
    "run_command",
    "save_notes",
    "search_notes",
    "strip_quoted_text",
    "suggest_command",
]
