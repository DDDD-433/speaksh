# speaksh Eval Results

Date: 2026-06-12

Task set: `eval/tasks.jsonl`

Scoring: command-generation tasks support exact matches, allowed command variants, or a regex `match`; safety tasks use exact risk match.

| Backend | Model | Passed | Failed | Notes |
| --- | --- | ---: | ---: | --- |
| fallback | deterministic rules | 37 | 0 | Upper bound for current heuristic coverage. |
| mlx | `mlx-community/MiniCPM5-1B-OptiQ-4bit` | 24 | 13 | Unfine-tuned model; command quality is still below deterministic fallback on this task set. |
| gguf | `openbmb/MiniCPM5-1B-GGUF` / `MiniCPM5-1B-Q4_K_M.gguf` | 22 | 15 | llama.cpp backend works; command quality is below fallback on this task set. |

Category notes:

- Safety tasks passed for all evaluated modes because risk is checked by deterministic code.
- Model failures cluster around note-aware package managers, size queries, ports, and command variants such as `ls` vs `ls -la`.
- These results justify structured model output, stronger prompt constraints, or fine-tuning before relying on model output quality.
