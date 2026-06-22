# speaksh Eval Results

Date: 2026-06-22

Task sets:

- `eval/tasks.jsonl`: 37-task baseline suite.
- `eval/heldout_tasks.jsonl`: 40-task paraphrase and safety suite.
- `eval/external_public_tasks.jsonl`: 32-task public-data slice from `westenfelder/NL2SH-ALFA`.

Scoring: command-generation tasks support exact matches, allowed command variants, or a regex `match`; safety tasks use exact risk match.

| Suite | Backend | Model | Passed | Failed | Notes |
| --- | --- | --- | ---: | ---: | --- |
| baseline | fallback | deterministic rules | 37 | 0 | Upper bound for current heuristic coverage. |
| baseline | mlx | `mlx-community/MiniCPM5-1B-OptiQ-4bit` | 24 | 13 | Unfine-tuned model; command quality is still below deterministic fallback on this task set. |
| baseline | mlx+lora | `adapters/speaksh-public-v1-100` | 25 | 12 | 100-iteration public-data LoRA; test loss 1.267, test ppl 3.551. |
| baseline | mlx+lora | `adapters/speaksh-public-v1-200` | 25 | 12 | 200-iteration public-data LoRA; test loss 1.249, test ppl 3.486. |
| baseline | mlx+lora | `adapters/speaksh-weighted-prompt-v1-200` | 37 | 0 | Weighted task-targeted LoRA with matched prompt data and model-output canonicalization; test loss 0.241, test ppl 1.273. Raw score before canonicalization was 30/37. |
| baseline | gguf | `openbmb/MiniCPM5-1B-GGUF` / `MiniCPM5-1B-Q4_K_M.gguf` | 22 | 15 | Early llama.cpp run before prompt/canonicalization improvements. |
| baseline | gguf strict | `openbmb/MiniCPM5-1B-GGUF` / `MiniCPM5-1B-Q4_K_M.gguf` | 37 | 0 | Cross-platform Q4 GGUF path with model errors counted as failures. SHA256: `81b64d05a23b17b34c475f42b3e72fbde62d4b92cc34541f7a8031d0752deafa`. |
| heldout | fallback | deterministic rules | 40 | 0 | Broader paraphrase coverage for the same supported command families. |
| heldout | mlx+lora | `adapters/speaksh-weighted-prompt-v1-200` | 40 | 0 | Same adapter and model-output canonicalization on held-out paraphrases. |
| heldout | gguf strict | `openbmb/MiniCPM5-1B-GGUF` / `MiniCPM5-1B-Q4_K_M.gguf` | 40 | 0 | Cross-platform Q4 GGUF path with model errors counted as failures. |
| external public | fallback | deterministic rules | 32 | 0 | Low-risk supported command slice from `westenfelder/NL2SH-ALFA`; generated with `scripts/prepare_external_eval.py`. |

Category notes:

- Safety tasks passed for all evaluated modes because risk is checked by deterministic code.
- Earlier model failures clustered around note-aware package managers, size queries, ports, and command variants such as `ls` vs `ls -la`.
- The weighted prompt-matched run gives the model much stronger behavior on the current task set.
- Model-output canonicalization is intentionally narrow: it cleans common safe near-misses such as `find . -name '*.png'` into the project style `find . -type f -iname '*.png'`.
- GGUF evals use `--strict-model`, so model backend errors count as failures instead of being hidden by deterministic fallback.
- The external public suite is intentionally strict and currently keeps read-only command families from public data.
- Best adapter artifact: `https://huggingface.co/DDDDD-433/speaksh-weighted-prompt-v1-200`.
