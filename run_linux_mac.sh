#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
[ -f .env ] || cp .env.example .env
if command -v git >/dev/null 2>&1 && [ -d .git ]; then
  echo "Checking GitHub for JARVIS updates..."
  python auto_update.py || echo "Update skipped/failed safely; continuing with current files."
fi
python jarvis_v2.py
