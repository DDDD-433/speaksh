# speaksh Eval Results

Date: 2026-06-20

Task set: `eval/tasks.jsonl`

Scoring: command-generation tasks support exact matches, allowed command variants, or a regex `match`; safety tasks use exact risk match.

| Backend | Model | Passed | Failed | Notes |
| --- | --- | ---: | ---: | --- |
| fallback | deterministic rules | 37 | 0 | Upper bound for current heuristic coverage. |
| mlx | `mlx-community/MiniCPM5-1B-OptiQ-4bit` | 24 | 13 | Unfine-tuned model; command quality is still below deterministic fallback on this task set. |
| mlx+lora | `adapters/speaksh-public-v1-100` | 25 | 12 | 100-iteration public-data LoRA; test loss 1.267, test ppl 3.551. |
| mlx+lora | `adapters/speaksh-public-v1-200` | 25 | 12 | 200-iteration public-data LoRA; test loss 1.249, test ppl 3.486. |
| mlx+lora | `adapters/speaksh-weighted-prompt-v1-200` | 37 | 0 | Weighted task-targeted LoRA with matched prompt data and model-output canonicalization; test loss 0.241, test ppl 1.273. Raw score before canonicalization was 30/37. |
| gguf | `openbmb/MiniCPM5-1B-GGUF` / `MiniCPM5-1B-Q4_K_M.gguf` | 22 | 15 | llama.cpp backend works; command quality is below fallback on this task set. |

Category notes:

- Safety tasks passed for all evaluated modes because risk is checked by deterministic code.
- Earlier model failures clustered around note-aware package managers, size queries, ports, and command variants such as `ls` vs `ls -la`.
- The weighted prompt-matched run gives the model much stronger behavior on the current task set.
- Model-output canonicalization is intentionally narrow: it cleans common safe near-misses such as `find . -name '*.png'` into the project style `find . -type f -iname '*.png'`.
- The next eval step should add more held-out natural-language variants so the benchmark is less tied to exact training prompts.
