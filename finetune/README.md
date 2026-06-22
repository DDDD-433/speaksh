# speaksh fine-tuning

Checkpoint 5A prepares public-data fine-tuning inputs for the default local
model:

```text
mlx-community/MiniCPM5-1B-OptiQ-4bit
```

Install training extras:

```bash
pip install -e '.[train]'
```

Prepare the public curated dataset:

```bash
python scripts/prepare_finetune_data.py \
  --preset public-curated-v1
```

Run a small MLX-LM LoRA job:

```bash
mlx_lm.lora \
  --model mlx-community/MiniCPM5-1B-OptiQ-4bit \
  --train \
  --data data/processed/speaksh_public_v1/mlx \
  --adapter-path adapters/speaksh-public-v1 \
  --iters 600 \
  --batch-size 2 \
  --learning-rate 2e-5 \
  --max-seq-length 2048 \
  --steps-per-report 10 \
  --steps-per-eval 100
```

Checkpoint 5B smoke test:

```bash
mlx_lm.lora \
  --model mlx-community/MiniCPM5-1B-OptiQ-4bit \
  --train \
  --data data/processed/speaksh_public_v1/mlx \
  --adapter-path adapters/smoke-5b \
  --iters 1 \
  --batch-size 1 \
  --learning-rate 1e-5 \
  --max-seq-length 512 \
  --steps-per-report 1 \
  --steps-per-eval 1 \
  --val-batches 1 \
  --save-every 1
```

Observed smoke result:

```text
Train loss: 7.623
Val loss: 8.360
Peak memory: 1.100 GB
Adapter: adapters/smoke-5b/adapters.safetensors
```

Adapter test command:

```bash
mlx_lm.lora \
  --model mlx-community/MiniCPM5-1B-OptiQ-4bit \
  --data data/processed/speaksh_public_v1/mlx \
  --adapter-path adapters/smoke-5b \
  --test \
  --test-batches 1 \
  --max-seq-length 512
```

Observed adapter test result:

```text
Test loss: 6.841
Test ppl: 935.430
```

Run the CLI with a local adapter:

```bash
speaksh --adapter-path adapters/smoke-5b --dry-run "find pdf files"
```

Run the eval harness with a local adapter:

```bash
python scripts/eval.py \
  --model-backend mlx \
  --adapter-path adapters/smoke-5b
```

The 1-iteration smoke adapter proves the loading path works; it is not expected
to improve command quality. Run a longer LoRA pass before treating adapter evals
as meaningful.

## Short LoRA runs

Two short local runs were tested after the 1-iteration smoke:

```text
adapters/speaksh-public-v1-100
  iters: 100
  max_seq_length: 1024
  final val loss: 1.169
  test loss: 1.267
  test ppl: 3.551
  eval/tasks.jsonl: 25/37

adapters/speaksh-public-v1-200
  iters: 200
  max_seq_length: 512
  final val loss: 1.352
  test loss: 1.249
  test ppl: 3.486
  eval/tasks.jsonl: 25/37
```

The lower test loss shows the model is learning the public NL-to-shell format.
The task harness improves only slightly over the base MLX model. The current
data pipeline now includes a small task-targeted source for note-aware package
manager selection, size queries, port/process lookups, and compression commands;
the next adapter run should regenerate the data and train against that updated
mix.

## Weighted task-targeted run

The task-targeted source can be kept in training and repeated with:

```json
{
  "destination": "train_only",
  "train_repeat": 120
}
```

Regenerate data after prompt or source-config changes:

```bash
python scripts/prepare_finetune_data.py \
  --preset public-curated-v1
```

The weighted prompt run used prompt-matched JSONL:

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

Observed result:

```text
final val loss: 0.279
test loss: 0.241
test ppl: 1.273
eval/tasks.jsonl: 37/37 with model-output canonicalization
raw adapter score before canonicalization: 30/37
```
