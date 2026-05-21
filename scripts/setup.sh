#!/usr/bin/env bash
set -euo pipefail

echo ">>> IA-Privada v3: setup no WSL"
sudo apt update
sudo apt install -y python3.12-venv python3-pip docker.io docker-compose-plugin

echo ">>> Criando venv e instalando dependências (modo WSL opcional)"
cd "$(dirname "$0")/../wsl"
python3 -m venv .venv || true
source .venv/bin/activate || true
python -m pip install --upgrade pip setuptools wheel || true
python -m pip install -r requirements.txt || true

echo ">>> Subindo serviços Docker (Ollama, OpenWebUI, Uploader)"
cd ..
docker compose up -d --build

echo ">>> Baixando modelos no Ollama"
../scripts/pull_models.sh || true

echo ">>> Testes rápidos"
../scripts/test_ollama.sh || true

echo ">>> Pronto! Acesse http://localhost:8081 (login definido no docker-compose.yml)"
