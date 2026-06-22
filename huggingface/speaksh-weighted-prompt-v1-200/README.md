---
license: mit
base_model: mlx-community/MiniCPM5-1B-OptiQ-4bit
library_name: mlx
tags:
  - text-generation
  - shell
  - cli
  - mlx
  - lora
  - natural-language-to-code
---

# speaksh-weighted-prompt-v1-200

LoRA adapter for `speaksh`, a local-first natural-language-to-shell command
CLI for Unix-like systems.

The adapter targets short command-generation requests for file search, disk
usage, process lookup, archive creation, package installation, and Git status.
The `speaksh` runtime applies deterministic safety checks and narrow command
canonicalization after generation.

## Base Model

```text
mlx-community/MiniCPM5-1B-OptiQ-4bit
```

## Intended Use

Use this adapter with the `speaksh` CLI for local command suggestion
experiments. It is intended for reviewed, interactive use, not unattended shell
automation.

Example:

```bash
speaksh \
  --adapter-path adapters/speaksh-weighted-prompt-v1-200 \
  --dry-run "find files over 100mb"
```

## Training Data

The training pipeline uses permissive public NL-to-shell datasets:

- `westenfelder/NL2SH-ALFA` - MIT
- `emirkaanozdemr/bash_command_data_6K` - Apache-2.0
- `AryaYT/nl2shell-training-v3` - Apache-2.0

It also includes a small MIT-licensed curated set for supported `speaksh`
command families:

- note-aware package manager selection
- size queries
- file search
- port and process lookup
- compression commands

Filtering removes dangerous commands, multiline commands, empty examples, and
benchmark-specific `/testbed` paths before training.

## Training Command

```bash
mlx_lm.lora \
  --model mlx-community/MiniCPM5-1B-OptiQ-4bit \
  --train \
  --data data/processed/speaksh_public_v1/mlx \
  --adapter-path adapters/speaksh-weighted-prompt-v1-200 \
  --iters 200 \
  --batch-size 2 \
  --learning-rate 2e-5 \
  --max-seq-length 512 \
  --steps-per-report 20 \
  --steps-per-eval 50 \
  --val-batches 25 \
  --save-every 100 \
  --seed 42
```

## Results

```text
Final validation loss: 0.279
Test loss: 0.241
Test perplexity: 1.273
Baseline speaksh eval: 37/37
Held-out speaksh eval: 40/40
External public fallback eval: 32/32
Raw adapter baseline score before command canonicalization: 30/37
```

The `speaksh` eval scores include runtime safety classification and narrow
command canonicalization.

## Safety And Limitations

- This adapter is not a sandbox.
- Commands should be reviewed before execution.
- The runtime blocks commands classified as dangerous unless explicitly
  overridden.
- The benchmark is exact-match oriented and does not cover every valid shell
  formulation.
- Windows and PowerShell are not supported.

## Links

- GitHub: https://github.com/DDDD-433/speaksh
