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

# speaksh-public-v1-200

LoRA adapter for `speaksh`, a local-first natural-language shell command
assistant for Unix-like systems.

This adapter is trained from public NL-to-shell datasets and is intended for
local experimentation with the `speaksh` CLI. It is not a sandbox and should
not be used without command review and safety checks.

## Base model

```text
mlx-community/MiniCPM5-1B-OptiQ-4bit
```

## Training data

The training pipeline uses permissive public datasets:

- `westenfelder/NL2SH-ALFA` - MIT
- `emirkaanozdemr/bash_command_data_6K` - Apache-2.0
- `AryaYT/nl2shell-training-v3` - Apache-2.0

Dangerous commands, multiline commands, empty examples, and benchmark-specific
`/testbed` paths are filtered before training.

## Training command

```bash
mlx_lm.lora \
  --model mlx-community/MiniCPM5-1B-OptiQ-4bit \
  --train \
  --data data/processed/speaksh_public_v1/mlx \
  --adapter-path adapters/speaksh-public-v1-200 \
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
Final validation loss: 1.352
Test loss: 1.249
Test perplexity: 3.486
speaksh task harness: 25/37
```

The adapter substantially improves language-model loss on public NL-to-shell
data. The small task harness improves only slightly over the base MLX model, so
future work should use more task-targeted data and richer command evaluation.

## Usage

```bash
speaksh --adapter-path adapters/speaksh-public-v1-200 --dry-run "find pdf files"
```

## Safety

`speaksh` runs deterministic safety classification on the final command before
execution. Generated commands should still be reviewed by the user.

## Links

- GitHub: https://github.com/DDDD-433/speaksh
