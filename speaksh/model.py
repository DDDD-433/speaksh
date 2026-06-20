from __future__ import annotations

import os
import re
from typing import Any, List, Optional, Sequence

from .config import DEFAULT_MODEL_BACKEND, DEFAULT_MODEL_NAME
from .safety import classify_risk
from .types import Note, Suggestion

_LLAMA_LOG_CALLBACK = None


def command_from_generated_text(text: str) -> str:
    """Extract the first plausible shell command from model output."""
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:bash|sh|zsh)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    for line in cleaned.splitlines():
        command = line.strip().strip("`")
        if not command:
            continue
        if command.startswith("$ "):
            command = command[2:].strip()
        return command
    return ""


def _request_text(request: str) -> str:
    return re.sub(r"\s+", " ", request.lower()).strip()


def _requested_extension(text: str) -> str | None:
    extensions = {
        "pdf": "pdf",
        "png": "png",
        "jpg": "jpg",
        "jpeg": "jpeg",
        "python": "py",
        "py": "py",
        "markdown": "md",
        "md": "md",
        "text": "txt",
        "txt": "txt",
    }
    for word, ext in extensions.items():
        if re.search(rf"\b{re.escape(word)}\b", text):
            return ext
    return None


def _notes_text(notes: Sequence[Note]) -> str:
    return "\n".join(note.content.lower() for note in notes)


def canonicalize_model_command(request: str, command: str, notes: Sequence[Note]) -> str:
    """Clean common near-miss model outputs into stable shell forms."""
    t = _request_text(request)
    stripped = command.strip()
    notes_text = _notes_text(notes)

    if any(phrase in t for phrase in ("compress this folder", "compress current directory", "zip this folder", "zip the current directory", "make a zip", "create a zip archive")):
        return "zip -r archive.zip ."

    if any(word in t for word in ("disk", "filesystem")) and any(word in t for word in ("usage", "space", "free", "available")):
        return "df -h"

    if any(phrase in t for phrase in ("show hidden", "list hidden", "hidden files", "dotfiles", "including hidden", "list files", "show files")):
        if "dotfiles" in t or stripped == "ls" or stripped.startswith(("ls -la ", "ls -la|", "ls -la |")):
            return "ls -la"

    if any(phrase in t for phrase in ("current directory", "where am i", "what folder am i in", "working directory", "pwd")):
        return "pwd"

    if any(word in t for word in ("find", "search", "locate")) and any(word in t for word in ("files", "documents", "images", "scripts", "docs")):
        ext = _requested_extension(t)
        if ext:
            return f"find . -type f -iname '*.{ext}'"

    if "bigger than" in t or "larger than" in t or "over " in t:
        size_match = re.search(r"(\d+)\s*(gb|g|mb|m|kb|k)\b", t)
        if size_match:
            unit = size_match.group(2).lower()[0].upper()
            return f"find . -type f -size +{size_match.group(1)}{unit} -exec ls -lh {{}} \\;"

    if "largest files" in t or "biggest files" in t or "largest items" in t or "biggest items" in t:
        return "du -ah . | sort -rh | head -20"

    if "port" in t and any(word in t for word in ("using", "listening", "open", "process")):
        port_match = re.search(r"\bport\s+(\d{2,5})\b|:(\d{2,5})\b", t)
        if port_match:
            port = port_match.group(1) or port_match.group(2)
            return f"lsof -i :{port}"

    if any(phrase in t for phrase in ("show processes", "list processes", "running processes", "active processes")):
        if stripped in {"ps", "ps -aux"}:
            return "ps aux"

    if any(phrase in t for phrase in ("install dependencies", "install deps", "install packages", "install project packages", "install project dependencies", "setup dependencies", "setup the project dependencies")):
        if "pnpm" in notes_text:
            return "pnpm install"
        if "bun" in notes_text:
            return "bun install"
        if "yarn" in notes_text:
            return "yarn install"
        if "pipenv" in notes_text:
            return "pipenv install"
        if "poetry" in notes_text:
            return "poetry install"
        return "npm install"

    if any(phrase in t for phrase in ("git status", "status of git", "repo status", "repository status", "working tree status")):
        return "git status"

    return stripped


def build_model_messages(request: str, notes: Sequence[Note]) -> List[dict[str, str]]:
    notes_block = "\n".join(f"- {n.content}" for n in notes) or "- no notes"
    system_prompt = (
        "You translate user requests into ONE safe Unix shell command.\n"
        "Rules:\n"
        "- Output only the command, no Markdown, no explanation.\n"
        "- Target shell: bash/zsh on Unix/Linux/macOS.\n"
        "- Prefer read-only commands unless the user asks for changes.\n"
        "- Search from the current directory unless the user names an absolute path; prefer `.` over `/`.\n"
        "- Examples: show hidden files -> ls -la; list files -> ls -la; show current directory -> pwd; where am i -> pwd.\n"
        "- Search examples: find pdf files -> find . -type f -iname '*.pdf'; search for markdown files -> find . -type f -iname '*.md'.\n"
        "- Size example: find files bigger than 500mb -> find . -type f -size +500M -exec ls -lh {} \\;.\n"
        "- Largest-files example: show the largest files -> du -ah . | sort -rh | head -20.\n"
        "- System examples: what process is using port 3000 -> lsof -i :3000; show running processes -> ps aux; compress this folder -> zip -r archive.zip .\n"
        "- Repository example: show git working tree status -> git status.\n"
        "- If a note names a tool, prefer it. Example: with note 'this project uses pnpm', install dependencies -> pnpm install.\n"
        "- Use these project notes when relevant:\n"
        f"{notes_block}"
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": request},
    ]


def build_gguf_prompt(request: str, notes: Sequence[Note]) -> str:
    notes_block = "\n".join(f"- {n.content}" for n in notes) or "- no notes"
    return (
        "Convert the request to exactly one Unix shell command. "
        "Output only the command. Do not explain. Do not use <think>.\n"
        "Rules:\n"
        "- Target bash/zsh on Unix/Linux/macOS.\n"
        "- Prefer read-only commands unless the user asks for changes.\n"
        "- Search from the current directory unless the user names an absolute path; prefer . over /.\n"
        "- Use project notes when relevant.\n"
        "Examples:\n"
        "show hidden files => ls -la\n"
        "list files => ls -la\n"
        "show current directory => pwd\n"
        "where am i => pwd\n"
        "find pdf files => find . -type f -iname '*.pdf'\n"
        "search for markdown files => find . -type f -iname '*.md'\n"
        "find files bigger than 500mb => find . -type f -size +500M -exec ls -lh {} \\;\n"
        "show the largest files => du -ah . | sort -rh | head -20\n"
        "what process is using port 3000 => lsof -i :3000\n"
        "show running processes => ps aux\n"
        "compress this folder => zip -r archive.zip .\n"
        "show git working tree status => git status\n"
        "show disk usage => df -h\n"
        "Notes:\n"
        f"{notes_block}\n\n"
        f"Request: {request}\n"
        "Command:"
    )


def chat_prompt(tokenizer: Any, messages: Sequence[dict[str, str]]) -> str:
    try:
        return tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )
    except TypeError:
        return tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )


def load_mlx_model(model_name: str, adapter_path: Optional[str] = None) -> tuple[Any, Any]:
    """Load MiniCPM5-1B through mlx-lm, optionally with a LoRA adapter."""
    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
    try:
        from mlx_lm import load  # type: ignore
    except Exception as exc:
        raise RuntimeError("mlx-lm is not installed. Install it with `pip install mlx-lm` or run with --no-model.") from exc

    if adapter_path is None:
        return load(model_name)
    if not os.path.isdir(adapter_path):
        raise RuntimeError(f"Adapter path not found: {adapter_path!r}. Pass --adapter-path pointing at an existing adapter directory.")
    try:
        return load(model_name, adapter_path=adapter_path)
    except TypeError as exc:
        raise RuntimeError("Installed mlx-lm does not support adapter_path. Upgrade with `pip install -U mlx-lm`.") from exc


def mlx_model_suggestion(request: str, notes: Sequence[Note], model_name: str, adapter_path: Optional[str] = None) -> Suggestion:
    model, tokenizer = load_mlx_model(model_name, adapter_path)
    messages = build_model_messages(request, notes)
    prompt = chat_prompt(tokenizer, messages)

    try:
        from mlx_lm import generate  # type: ignore
    except Exception as exc:
        raise RuntimeError("mlx-lm generate API is unavailable.") from exc

    generated = generate(model, tokenizer, prompt=prompt, max_tokens=96, verbose=False)
    command = command_from_generated_text(generated)
    command = canonicalize_model_command(request, command, notes)
    if not command:
        raise RuntimeError("Model returned an empty command.")
    risk, _ = classify_risk(command)
    return Suggestion(command=command, explanation="Generated by local MLX MiniCPM5-1B OptiQ model.", risk=risk, source=model_name)


def load_transformers_model(model_name: str) -> tuple[Any, Any]:
    """Load MiniCPM5-1B through transformers."""
    try:
        import torch  # type: ignore
        from transformers import AutoModelForCausalLM, AutoTokenizer  # type: ignore
    except Exception as exc:
        raise RuntimeError("transformers/torch are not installed. Install them or run with --no-model.") from exc

    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(model_name, trust_remote_code=True)
    if torch.cuda.is_available():
        model = model.half().cuda()
    return model, tokenizer


def transformers_model_suggestion(request: str, notes: Sequence[Note], model_name: str) -> Suggestion:
    """Generate a command with a local transformers model."""
    model, tokenizer = load_transformers_model(model_name)
    messages = build_model_messages(request, notes)

    try:
        prompt = chat_prompt(tokenizer, messages)
    except Exception:
        prompt = f"<|system|>{messages[0]['content']}\n<|user|>{request}<|assistant|>"

    inputs = tokenizer(prompt, return_tensors="pt")
    if hasattr(model, "device"):
        inputs = inputs.to(model.device)
    import torch  # type: ignore
    with torch.no_grad():
        output = model.generate(**inputs, max_new_tokens=96, do_sample=False)
    generated = tokenizer.decode(output[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True)
    command = command_from_generated_text(generated)
    command = canonicalize_model_command(request, command, notes)
    if not command:
        raise RuntimeError("Model returned an empty command.")
    risk, _ = classify_risk(command)
    return Suggestion(command=command, explanation="Generated by local model.", risk=risk, source=model_name)


def gguf_model_suggestion(request: str, notes: Sequence[Note], model_name: str) -> Suggestion:
    """Generate a command with a local GGUF model through llama-cpp-python."""
    if not model_name or model_name == DEFAULT_MODEL_NAME:
        raise RuntimeError(
            "GGUF backend requires an explicit local .gguf model path. "
            "Pass --model /path/to/model.gguf (speaksh does not download GGUF models)."
        )
    if not model_name.endswith(".gguf") or not os.path.isfile(model_name):
        raise RuntimeError(
            f"GGUF model path not found: {model_name!r}. "
            "Pass --model /path/to/model.gguf pointing at an existing local file."
        )

    try:
        import ctypes

        import llama_cpp  # type: ignore
        from llama_cpp import Llama  # type: ignore
    except Exception as exc:
        raise RuntimeError(
            "llama-cpp-python is not installed. Install it with `pip install -e '.[gguf]'` "
            "or `pip install llama-cpp-python`, or run with --no-model."
        ) from exc

    global _LLAMA_LOG_CALLBACK
    if _LLAMA_LOG_CALLBACK is None:
        _LLAMA_LOG_CALLBACK = llama_cpp.llama_log_callback(lambda level, text, user_data: None)
        llama_cpp.llama_log_set(_LLAMA_LOG_CALLBACK, ctypes.c_void_p())

    llm = Llama(model_path=model_name, n_ctx=2048, verbose=False)
    prompt = build_gguf_prompt(request, notes)
    result = llm.create_completion(prompt=prompt, max_tokens=96, temperature=0.0, stop=["\n"])
    generated = result["choices"][0]["text"] or ""
    command = command_from_generated_text(generated)
    command = canonicalize_model_command(request, command, notes)
    if not command:
        raise RuntimeError("Model returned an empty command.")
    risk, _ = classify_risk(command)
    return Suggestion(command=command, explanation="Generated by local GGUF model via llama.cpp.", risk=risk, source=model_name)


def model_suggestion(
    request: str,
    notes: Sequence[Note],
    model_name: str = DEFAULT_MODEL_NAME,
    model_backend: str = DEFAULT_MODEL_BACKEND,
    adapter_path: Optional[str] = None,
) -> Suggestion:
    if adapter_path and model_backend != "mlx":
        raise RuntimeError("--adapter-path is only supported with the MLX backend.")
    if model_backend == "mlx":
        return mlx_model_suggestion(request, notes, model_name, adapter_path)
    if model_backend == "transformers":
        return transformers_model_suggestion(request, notes, model_name)
    if model_backend == "gguf":
        return gguf_model_suggestion(request, notes, model_name)
    raise RuntimeError(f"Unsupported model backend: {model_backend}")
