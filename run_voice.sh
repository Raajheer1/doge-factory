#!/usr/bin/env bash
# Start the local Mobilize API from any working directory.
set -euo pipefail
cd "$(dirname "$0")"

if [[ ! -x .venv/bin/python ]]; then
  python_cmd=''
  for candidate in python3 python3.14 python3.13 python3.12 python3.11; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; sys.exit(sys.version_info < (3, 11))'; then
      python_cmd="$candidate"
      break
    fi
  done
  if [[ -n "$python_cmd" ]]; then
    echo "Creating .venv with $python_cmd..."
    "$python_cmd" -m venv .venv
  else
    if ! command -v python3 >/dev/null 2>&1; then
      echo 'Python 3 is required to install the Python 3.11 runtime.' >&2
      exit 1
    fi
    echo 'Python 3.11+ not found. Installing a local runtime using uv...'
    bootstrap="$PWD/data/voice-bootstrap"
    if [[ ! -x "$bootstrap/bin/uv" ]]; then
      python3 -m pip install --upgrade --target "$bootstrap" uv
    fi
    "$bootstrap/bin/uv" venv --seed --python 3.11 --python-preference only-managed .venv
  fi
fi

if ! .venv/bin/python -c 'import sys; sys.exit(sys.version_info < (3, 11))'; then
  echo 'The existing .venv needs Python 3.11 or newer. Recreate it with a supported Python version.' >&2
  exit 1
fi

# Reinstall when dependencies change after a pull, or when the console cannot
# import. Write the stamp only after a successful install.
manifest_hash=$(.venv/bin/python -c 'import hashlib; print(hashlib.sha256(open("pyproject.toml", "rb").read()).hexdigest())')
stamp=.venv/.voice-dependencies-sha256
installed_hash=''
if [[ -f "$stamp" ]]; then installed_hash=$(<"$stamp"); fi
if [[ ! -x .venv/bin/voice-agents ]] || [[ "$manifest_hash" != "$installed_hash" ]] || ! .venv/bin/python -c 'import voice_agents.console.server' >/dev/null 2>&1; then
  echo 'Installing or updating voice agent dependencies...'
  .venv/bin/python -m pip install -e '.[console]'
  printf '%s\n' "$manifest_hash" > "$stamp"
fi

if [[ ! -f .env ]]; then
  echo 'Note: .env not found. Copy .env.example to .env and configure credentials for live calls.' >&2
fi

echo 'Starting the Mobilize API at http://127.0.0.1:8000 (Ctrl+C to stop)...'
exec .venv/bin/voice-agents console
