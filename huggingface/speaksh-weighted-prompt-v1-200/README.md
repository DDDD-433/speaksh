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

LoRA adapter for `speaksh`, a local-first natural-language shell command
assistant for Unix-like systems.

This adapter targets short command-generation requests such as file search,
disk usage, process lookup, archive creation, package installation, and Git
status. It is designed to run with the `speaksh` CLI, which applies deterministic
safety checks and narrow command canonicalization after model generation.

## Base Model

```text
mlx-community/MiniCPM5-1B-OptiQ-4bit
```

## Training Data

The training pipeline uses permissive public NL-to-shell datasets:

- `westenfelder/NL2SH-ALFA` - MIT
- `emirkaanozdemr/bash_command_data_6K` - Apache-2.0
- `AryaYT/nl2shell-training-v3` - Apache-2.0

It also includes a small local MIT-licensed curated set for supported `speaksh`
command families:

- note-aware package manager selection
- size queries
- file search
- port and process lookup
- compression commands

Dangerous commands, multiline commands, empty examples, and benchmark-specific
`/testbed` paths are filtered before training. The curated source is kept in the
training split and repeated for short LoRA runs; it is not mixed into validation
or test splits.

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
Raw adapter baseline score before command canonicalization: 30/37
```

The 37/37 and 40/40 eval scores use the `speaksh` runtime, including
post-generation safety classification and narrow command canonicalization.

## Usage

Install `speaksh` and MLX-LM, then run:

```bash
speaksh \
  --adapter-path adapters/speaksh-weighted-prompt-v1-200 \
  --dry-run "find files over 100mb"
```

Run the bundled evals:

```bash
python scripts/eval.py \
  --model-backend mlx \
  --adapter-path adapters/speaksh-weighted-prompt-v1-200

python scripts/eval.py \
  --model-backend mlx \
  --adapter-path adapters/speaksh-weighted-prompt-v1-200 \
  --tasks eval/heldout_tasks.jsonl
```

## Safety

This adapter is not a sandbox. It can still generate incorrect or unsafe shell
commands. `speaksh` classifies risk on the final command before execution, but
users should review commands before running them.

## Links

- GitHub: https://github.com/DDDD-433/speaksh
