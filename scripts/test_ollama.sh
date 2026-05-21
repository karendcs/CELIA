#!/usr/bin/env bash
set -euo pipefail
echo "Testando Ollama (host):"
curl -s http://localhost:11434/api/tags | head -c 500; echo
echo "Testando do container 'uploader':"
docker compose exec uploader bash -lc "curl -s http://ollama:11434/api/tags | head -c 500; echo"
