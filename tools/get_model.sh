#!/usr/bin/env bash
# Download the small instruct model used by the optional local AI assist (about 1 GB).
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p models
URL="https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf"
OUT="models/qwen2.5-1.5b-instruct-q4_k_m.gguf"
if [ -f "$OUT" ]; then echo "already have $OUT"; exit 0; fi
curl -L --fail --progress-bar -o "$OUT.part" "$URL" && mv "$OUT.part" "$OUT"
echo "saved $OUT"
