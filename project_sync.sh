#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

CONFIG_PROVIDED=false
for arg in "$@"; do
  case "$arg" in
    --config | --config=*)
      CONFIG_PROVIDED=true
      ;;
  esac
done

if [ "$CONFIG_PROVIDED" = true ]; then
  exec python3 "$PROJECT_DIR/src/project_sync.py" "$@"
fi

exec python3 "$PROJECT_DIR/src/project_sync.py" --config "$PROJECT_DIR/repos.json" "$@"
