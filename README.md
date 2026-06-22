# speaksh

`speaksh` is a tiny, local-first terminal companion for Unix/Linux systems.
It turns plain English into Bash/Zsh-style commands, asks before running them,
and stores lightweight project notes locally.

This MVP is intentionally small:

- no GUI
- no cloud API calls
- no Windows/PowerShell support yet
- local model-first command generation

By default, `speaksh` tries to use the MLX OptiQ quant of MiniCPM5-1B:

```text
mlx-community/MiniCPM5-1B-OptiQ-4bit
```

The best local LoRA adapter is published on Hugging Face:

```text
https://huggingface.co/DDDDD-433/speaksh-weighted-prompt-v1-200
```

If MLX or the model is unavailable, it falls back to built-in rules so the CLI
still works. Use `--no-model` when you explicitly want deterministic fallback
mode.

## Features

- **One-shot command mode**: `speaksh "show hidden files"`
- **Interactive mode**: `speaksh`
- **Notes**: `note add`, `note list`, `note search`
- **Note-aware suggestions**: notes can influence command suggestions, such as using `pnpm install` when a project note says the repo uses pnpm
- **Safety checks**: command risk classification before execution
- **Dry-run mode**: print suggested commands without prompting or running
- **Local history**: request/command history in JSONL

## Install

```bash
python3 --version
```

Python 3.10+ is enough for fallback mode.

Lightweight install:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
```

Apple Silicon / MLX model install:

```bash
python -m pip install -e '.[mlx]'
```

Check the install:

```bash
speaksh --version
speaksh doctor
speaksh --no-model --dry-run "show hidden files"
```

## Development

Run the same checks used by CI:

```bash
python -m unittest -v
python scripts/eval.py --no-model
python scripts/eval.py --no-model --tasks eval/heldout_tasks.jsonl
python scripts/eval.py --no-model --tasks eval/external_public_tasks.jsonl
```

## Usage

### One-shot mode

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

Show explanations:

```bash
speaksh --dry-run --explain "find pdf files"
```

Use deterministic fallback mode without loading a model:

```bash
speaksh --no-model --dry-run "show hidden files"
```

### Interactive mode

```bash
speaksh
```

Then type:

```text
list files
note add this project uses pnpm
note list
exit
```

### Notes

```bash
speaksh note add "this project uses pnpm"
speaksh note list
speaksh note search pnpm
```

Notes are stored in:

```text
~/.speaksh/notes.json
```

History is stored in:

```text
~/.speaksh/history.jsonl
```

For isolated testing or per-project state, set:

```bash
export SPEAKSH_HOME=/tmp/my-speaksh-state
```

### Health check

```bash
speaksh doctor
```

This prints Python, state directory, backend, model, and backend dependency
availability without loading the model.

### Eval wrapper

```bash
speaksh eval --no-model
```

This runs the bundled eval benchmark through the same harness as
`python scripts/eval.py`.

## MiniCPM5-1B support

The MVP uses MiniCPM5-1B as the main local brain. The default model is the MLX
OptiQ 4-bit quant:

```text
mlx-community/MiniCPM5-1B-OptiQ-4bit
```

Run with the default MLX backend:

```bash
speaksh "find files bigger than 500mb"
```

Override the model path if needed:

```bash
speaksh --model mlx-community/MiniCPM5-1B-OptiQ-4bit "find pdf files"
```

Run with a local MLX LoRA adapter:

```bash
speaksh --adapter-path adapters/smoke-5b --dry-run "find pdf files"
```

Best published adapter:

```text
DDDDD-433/speaksh-weighted-prompt-v1-200
```

`--adapter-path` is supported only with the MLX backend. Adapter directories
are local artifacts and are ignored by git.

The older Transformers backend is still available for the unquantized base
model:

```bash
speaksh --model-backend transformers --model openbmb/MiniCPM5-1B "find pdf files"
```

If the model or dependency is unavailable, `speaksh` prints a warning and falls
back to built-in rules. Safety classification always runs on the final command,
whether it came from the model or from heuristics.

## GGUF backend (optional)

`speaksh` can also run a local GGUF quant through `llama-cpp-python`. This is
opt-in: `llama-cpp-python` is not a base dependency, and `speaksh` never
downloads GGUF files for you.

Install the optional dependency:

```bash
pip install -e '.[gguf]'
```

Run with an explicit local `.gguf` model path:

```bash
speaksh --model-backend gguf --model /path/to/MiniCPM5-1B.Q4_K_M.gguf "find pdf files"
```

Download the tested MiniCPM5-1B Q4 GGUF:

```bash
mkdir -p models/gguf
hf download openbmb/MiniCPM5-1B-GGUF MiniCPM5-1B-Q4_K_M.gguf --local-dir models/gguf
```

The GGUF backend requires an explicit `--model` path to an existing local
`.gguf` file; there is no default GGUF model. If `llama-cpp-python` is missing
or the path is wrong, `speaksh` prints a warning and falls back to built-in
rules, the same as the other backends. `--no-model` always bypasses every
model backend.

## Eval benchmark

Small local eval benchmarks check command quality for both the fallback rules
and the model. The baseline suite lives in `eval/tasks.jsonl`; the broader
paraphrase suite lives in `eval/heldout_tasks.jsonl`; the small public-data
slice lives in `eval/external_public_tasks.jsonl`. Each line is either a
`fallback` task or a `safety` task. Fallback tasks can use `expected_command`,
`expected_commands`, or a regex `match` field, so known-good command variants
can pass without weakening safety checks. Tasks may carry an optional
`category` field used for the per-category summary. Every task runs against a
fresh temporary `SPEAKSH_HOME`, so evals never touch `~/.speaksh`.

Run the fallback eval (no model loaded, fast, dependency-free):

```bash
python scripts/eval.py --no-model
python scripts/eval.py --no-model --tasks eval/heldout_tasks.jsonl
python scripts/eval.py --no-model --tasks eval/external_public_tasks.jsonl
```

Run the model-backed eval (requires `mlx-lm` and the cached model):

```bash
.venv/bin/python scripts/eval.py
.venv/bin/python scripts/eval.py --tasks eval/heldout_tasks.jsonl
```

Optional backend/model flags work the same as the CLI:

```bash
.venv/bin/python scripts/eval.py --model-backend mlx --model mlx-community/MiniCPM5-1B-OptiQ-4bit
.venv/bin/python scripts/eval.py --model-backend gguf --model /path/to/model.gguf
.venv/bin/python scripts/eval.py --strict-model --model-backend gguf --model /path/to/model.gguf --tasks eval/heldout_tasks.jsonl
```

The script prints a per-task PASS/FAIL line, a `total/passed/failed` summary,
and a `by_category` breakdown:

```text
total=37 passed=37 failed=0
by_category:
  fallback_basic: 6/6
  fallback_notes: 5/5
  safety: 14/14
```

It exits non-zero if any task fails. Use `--tasks path/to/file.jsonl` to run a
custom task file. Use `--strict-model` when model-backed evals should count
model errors as failures instead of falling back to deterministic rules.

Current exact-match baselines are tracked in `eval/RESULTS.md`.

Current checked results:

```text
unit tests: 46/46
baseline eval: 37/37
heldout eval: 40/40
external public eval: 32/32
```

Regenerate the public-data eval slice:

```bash
python scripts/prepare_external_eval.py --limit-per-source 200 --max-tasks 32
```

This uses the public dataset source config, keeps low-risk supported commands
only, and writes deterministic JSONL with source and license metadata.

Note: scoring is exact string match against `expected_command`. That is the
right bar for the deterministic fallback, but it is strict for model-backed
runs — a semantically correct command with different flags or ordering counts
as a failure. There is no fuzzy/semantic scoring yet.

## Fine-tuning data pipeline

Checkpoint 5A adds a public-data pipeline for future MiniCPM5-1B LoRA
fine-tuning. It prepares permissive NL-to-shell datasets into canonical JSONL
and MLX-LM chat JSONL without changing the runtime CLI.

Install training extras:

```bash
pip install -e '.[train]'
```

Run a fast schema/dry-run check:

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

The MLX-LM training and adapter smoke-test commands are documented in
`finetune/README.md`.

## Tested flows

The included `tests/test_speaksh.py` test suite covers:

- one-shot command mode
- dry-run mode
- `--yes` execution mode
- default model-first routing
- `--no-model` fallback mode
- notes add/list/search
- note-aware dependency install suggestion
- interactive mode
- unknown request behavior
- dangerous-command classification
- eval harness pass/fail behavior
- public fine-tuning data normalization, filtering, splitting, manifests, and MLX-LM message output

Run tests:

```bash
python3 -m unittest -v
```

## Current limitations

- Fallback mode only understands a small set of common requests.
- Model inference is basic and should be improved before serious use.
- Safety is heuristic, not a formal sandbox.
- Unix/Linux/macOS shell support only; no native PowerShell support yet.

## Project direction

Good next steps:

1. Add a tiny dataset: natural language → Bash command.
2. Fine-tune MiniCPM5-1B LoRA for command generation.
3. Add stronger command parsing and risk classification.
4. Add a Textual/Ratatui TUI after the CLI is solid.
