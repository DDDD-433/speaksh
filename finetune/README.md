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
