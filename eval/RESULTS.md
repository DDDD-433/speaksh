# speaksh Eval Results

Date: 2026-06-12

Task set: `eval/tasks.jsonl`

Scoring: command-generation tasks support exact matches, allowed command variants, or a regex `match`; safety tasks use exact risk match.

| Backend | Model | Passed | Failed | Notes |
| --- | --- | ---: | ---: | --- |
| fallback | deterministic rules | 37 | 0 | Upper bound for current heuristic coverage. |
| mlx | `mlx-community/MiniCPM5-1B-OptiQ-4bit` | 24 | 13 | Unfine-tuned model; command quality is still below deterministic fallback on this task set. |
| mlx+lora | `adapters/speaksh-public-v1-100` | 25 | 12 | 100-iteration public-data LoRA; test loss 1.267, test ppl 3.551. |
| mlx+lora | `adapters/speaksh-public-v1-200` | 25 | 12 | 200-iteration public-data LoRA; test loss 1.249, test ppl 3.486. |
| gguf | `openbmb/MiniCPM5-1B-GGUF` / `MiniCPM5-1B-Q4_K_M.gguf` | 22 | 15 | llama.cpp backend works; command quality is below fallback on this task set. |

Category notes:

- Safety tasks passed for all evaluated modes because risk is checked by deterministic code.
- Model failures cluster around note-aware package managers, size queries, ports, and command variants such as `ls` vs `ls -la`.
- The LoRA runs greatly reduce language-model loss on the public NL-to-shell dataset, but only slightly improve this small task harness.
- These results justify better task-targeted data, stronger prompt constraints, and a richer semantic command evaluator before relying on model output quality.
