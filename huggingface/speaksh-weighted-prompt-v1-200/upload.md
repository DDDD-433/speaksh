# Upload notes

This directory contains the model card for publishing the best local adapter.
Do not commit adapter weights to GitHub.

Local adapter files:

```text
adapters/speaksh-weighted-prompt-v1-200/adapters.safetensors
adapters/speaksh-weighted-prompt-v1-200/adapter_config.json
```

SHA256:

```text
5d179e15643a1df9167210f24e307344e8433d778934d67a1e534d43cf294d9d  adapters.safetensors
baf83ac44543fa1ddd8c7797077f40f1a5fd0fc9acecaab1f4e3e1503de06a35  adapter_config.json
```

When Hugging Face auth is configured:

```bash
.venv/bin/hf auth login

.venv/bin/hf repos create DDDD-433/speaksh-weighted-prompt-v1-200 \
  --type model \
  --exist-ok

.venv/bin/hf upload DDDD-433/speaksh-weighted-prompt-v1-200 \
  adapters/speaksh-weighted-prompt-v1-200/adapters.safetensors \
  adapters.safetensors \
  --type model \
  --commit-message "Upload speaksh weighted prompt adapter"

.venv/bin/hf upload DDDD-433/speaksh-weighted-prompt-v1-200 \
  adapters/speaksh-weighted-prompt-v1-200/adapter_config.json \
  adapter_config.json \
  --type model \
  --commit-message "Add adapter config"

.venv/bin/hf upload DDDD-433/speaksh-weighted-prompt-v1-200 \
  huggingface/speaksh-weighted-prompt-v1-200/README.md \
  README.md \
  --type model \
  --commit-message "Add model card"
```

After upload, verify:

```bash
.venv/bin/hf models info DDDD-433/speaksh-weighted-prompt-v1-200
```
