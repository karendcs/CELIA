#!/usr/bin/env bash
set -euo pipefail
echo "Baixando modelos Ollama no host..."
curl http://localhost:11434/api/pull -d '{"name":"llama3:8b"}'
curl http://localhost:11434/api/pull -d '{"name":"nomic-embed-text"}'
echo "Concluído."
