# speaksh fine-tuning data

This directory tracks public dataset source metadata and local data-prep rules.
Generated datasets are intentionally ignored by git.

Current curated preset:

```text
public-curated-v1
```

Enabled sources are permissive public datasets only:

- `westenfelder/NL2SH-ALFA` - MIT
- `emirkaanozdemr/bash_command_data_6K` - Apache-2.0
- `AryaYT/nl2shell-training-v3` - Apache-2.0
- `speaksh/curated-task-targeted-v1` - MIT local curated rows for known weak eval areas

`carosh/cli-1m` is recorded but disabled by default because it is much broader
than the first speaksh fine-tuning target.

The local curated rows cover note-aware package manager selection, size
queries, port/process lookups, and compression commands. Rows may include
project notes so the MLX-LM training messages match the CLI prompt shape.

Generate local MLX-LM training files:

```bash
python scripts/prepare_finetune_data.py --preset public-curated-v1
```

Fast validation run:

```bash
python scripts/prepare_finetune_data.py --preset public-curated-v1 --limit-per-source 25 --dry-run
```

The generated files land under:

```text
data/processed/speaksh_public_v1/
```
