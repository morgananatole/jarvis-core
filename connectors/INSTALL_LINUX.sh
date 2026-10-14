#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m venv .executor-venv
.executor-venv/bin/python -m pip install -r connectors/requirements.txt
.executor-venv/bin/python -m connectors.setup --server "${1:?Informe a URL HTTPS do JARVIS}"
echo 'Instalado. Pareamento: .executor-venv/bin/python -m connectors.agent pair'
