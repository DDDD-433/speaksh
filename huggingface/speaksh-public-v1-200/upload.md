# Upload notes

This directory is a model-card template for publishing the local adapter.

When Hugging Face auth is configured:

```bash
.venv/bin/hf auth login
.venv/bin/hf repos create DDDD-433/speaksh-public-v1-200 --type model --exist-ok
.venv/bin/hf upload DDDD-433/speaksh-public-v1-200 adapters/speaksh-public-v1-200 . --type model --commit-message "Upload speaksh public v1 LoRA adapter"
.venv/bin/hf upload DDDD-433/speaksh-public-v1-200 huggingface/speaksh-public-v1-200/README.md README.md --type model --commit-message "Add model card"
```

Do not commit adapter weights to GitHub.
