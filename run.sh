#!/bin/bash
# Wrapper invoked by launchd every 2 minutes. Loads secrets from config.env
# and runs one poll cycle via uv (which uses the project's .venv).
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

if [[ -f config.env ]]; then
  set -a
  # shellcheck disable=SC1091
  source config.env
  set +a
else
  echo "$(date '+%Y-%m-%d %H:%M:%S') config.env missing — copy config.env.example" >&2
  exit 1
fi

exec uv run --quiet python poll.py
