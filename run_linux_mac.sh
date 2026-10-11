#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
if [ ! -d ".venv" ]; then python3 -m venv .venv; fi
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
if [ ! -f ".env" ] && [ -f ".env.example" ]; then cp .env.example .env; fi
if command -v git >/dev/null 2>&1 && [ -d ".git" ]; then
  echo "Checking GitHub for JARVIS updates..."
  python auto_update.py || true
fi
exec python jarvis.py
