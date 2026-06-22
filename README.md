# speaksh

`speaksh` is a local-first command-line tool that translates short natural
language requests into Unix shell commands. It combines a small local language
model, deterministic fallback rules, command risk classification, and
project-local notes.

The default model path targets Apple Silicon with MLX:

```text
mlx-community/MiniCPM5-1B-OptiQ-4bit
```

A LoRA adapter trained for the supported command families is published at:

```text
https://huggingface.co/DDDDD-433/speaksh-weighted-prompt-v1-200
```

If the model backend is unavailable, `speaksh` falls back to deterministic
rules. Use `--no-model` when you want fallback-only behavior.

## Features

- One-shot command suggestions: `speaksh "show hidden files"`
- Interactive terminal mode: `speaksh`
- Local notes: `speaksh note add/list/search`
- Note-aware command selection, for example `pnpm install` when notes mention pnpm
- Risk classification before command execution
- Dry-run mode for inspecting suggestions without running them
- Local JSONL history
- Optional MLX, Transformers, and GGUF model backends

## Install

Python 3.10+ is enough for fallback mode.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
```

Install MLX support on Apple Silicon:

```bash
python -m pip install -e '.[mlx]'
```

Check the install:

```bash
speaksh --version
speaksh doctor
speaksh --no-model --dry-run "show hidden files"
```

## Usage

One-shot dry run:

```bash
speaksh --dry-run "show hidden files"
```

Example output:

```text
Suggested command: ls -la
Risk: low
```

Run after confirmation:

```bash
speaksh "show current directory"
```

Run without confirmation:

```bash
speaksh --yes "show current directory"
```

Show the short explanation attached to a suggestion:

```bash
speaksh --dry-run --explain "find pdf files"
```

Use deterministic fallback mode:

```bash
speaksh --no-model --dry-run "show hidden files"
```

Interactive mode:

```bash
speaksh
```

Example note workflow:

```bash
speaksh note add "this project uses pnpm"
speaksh --no-model --dry-run "install dependencies"
```

Suggested command:

```text
pnpm install
```

Notes and history are stored locally under `~/.speaksh/`. For isolated test
runs, set `SPEAKSH_HOME`:

```bash
export SPEAKSH_HOME=/tmp/my-speaksh-state
```

## Model Support

Default MLX backend:

```bash
speaksh --model-backend mlx --model mlx-community/MiniCPM5-1B-OptiQ-4bit "find pdf files"
```

Run with a local MLX LoRA adapter:

```bash
speaksh \
  --adapter-path adapters/speaksh-weighted-prompt-v1-200 \
  --dry-run "find files over 100mb"
```

Published adapter:

```text
DDDDD-433/speaksh-weighted-prompt-v1-200
```

`--adapter-path` is supported only with the MLX backend. Adapter directories
are local artifacts and are ignored by git.

Transformers backend for the unquantized base model:

```bash
speaksh --model-backend transformers --model openbmb/MiniCPM5-1B "find pdf files"
```

Optional GGUF backend:

```bash
python -m pip install -e '.[gguf]'
mkdir -p models/gguf
hf download openbmb/MiniCPM5-1B-GGUF MiniCPM5-1B-Q4_K_M.gguf --local-dir models/gguf
speaksh --model-backend gguf --model models/gguf/MiniCPM5-1B-Q4_K_M.gguf "find pdf files"
```

The GGUF backend requires an explicit local `.gguf` path. `speaksh` does not
download GGUF files automatically.

## Safety

Every final command is classified before execution:

```text
low
medium
dangerous
```

Dangerous commands are blocked unless `--unsafe` is provided. This is not a
sandbox; users should review commands before running them.

## Evaluation

The eval harness uses JSONL task files under `eval/`. Command-generation tasks
support exact matches, accepted variants, or regex matches. Safety tasks require
an exact risk match.

Current checked results:

```text
unit tests: 46/46
baseline eval: 37/37
heldout eval: 40/40
external public eval: 32/32
```

Run the same fast checks used by CI:

```bash
python -m unittest -v
python scripts/eval.py --no-model
python scripts/eval.py --no-model --tasks eval/heldout_tasks.jsonl
python scripts/eval.py --no-model --tasks eval/external_public_tasks.jsonl
```

Model-backed eval examples:

```bash
python scripts/eval.py --model-backend mlx --model mlx-community/MiniCPM5-1B-OptiQ-4bit
python scripts/eval.py --model-backend gguf --model models/gguf/MiniCPM5-1B-Q4_K_M.gguf --strict-model
```

Detailed results are tracked in `eval/RESULTS.md`.

## Fine-Tuning Data

The data pipeline prepares permissive public NL-to-shell datasets into
canonical JSONL and MLX-LM chat JSONL.

Install training extras:

```bash
python -m pip install -e '.[train]'
```

Run a small dry run:

```bash
python scripts/prepare_finetune_data.py --preset public-curated-v1 --limit-per-source 25 --dry-run
```

Generate local training files:

```bash
python scripts/prepare_finetune_data.py --preset public-curated-v1
```

Generated data is ignored by git and written under:

```text
data/processed/speaksh_public_v1/
```

Regenerate the public eval slice:

```bash
python scripts/prepare_external_eval.py --limit-per-source 200 --max-tasks 32
```

Training and adapter evaluation commands are documented in `finetune/README.md`.

## Limitations

- Unix-like shell commands only
- No Windows or PowerShell support
- Not a sandbox
- Exact-match eval is useful for regression testing but does not measure every semantically valid command
- Model output quality depends on the local backend and adapter used

## Repository Notes

Large local artifacts are intentionally not committed:

- model weights
- LoRA adapter weights
- generated training data
- run logs
- private local context files
