#!/usr/bin/env bash
set -euo pipefail

# Run a command on the NAS inside APP_DIR directory.
# Usage: scripts/nas_exec.sh [ENV_FILE] -- <command>

ROOT_DIR="$(cd "$(dirname "$0")"/.. && pwd)"
ENV_FILE="$ROOT_DIR/.nas_deploy.env"

if [[ $# -ge 1 && "$1" != "--" ]]; then
  ENV_FILE="$1"; shift
fi

if [[ "${1:-}" == "--" ]]; then shift; fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "[nas-exec] ERROR: Env file not found: $ENV_FILE" >&2
  exit 1
fi

# shellcheck disable=SC1090
source "$ENV_FILE"

NAS_HOST="${NAS_HOST:-}"
NAS_USER="${NAS_USER:-}"
NAS_ALIAS="${NAS_ALIAS:-nas}"
APP_DIR="${APP_DIR:-}"

if [[ -z "$NAS_HOST" || -z "$NAS_USER" || -z "$APP_DIR" ]]; then
  echo "[nas-exec] ERROR: NAS_HOST, NAS_USER, and APP_DIR must be set in $ENV_FILE" >&2
  exit 2
fi

SSH_TARGET="$NAS_USER@$NAS_HOST"
if ssh -G "$NAS_ALIAS" >/dev/null 2>&1; then
  SSH_TARGET="$NAS_ALIAS"
fi

CMD=${*:-}
if [[ -z "$CMD" ]]; then
  echo "[nas-exec] ERROR: No command provided. Use: scripts/nas_exec.sh -- 'docker compose ps'" >&2
  exit 3
fi

echo "[nas-exec] Executing on $SSH_TARGET: $CMD"
ssh "$SSH_TARGET" "cd '$APP_DIR' && $CMD" || {
  exit_code=$?
  echo "[nas-exec] Command failed with exit code $exit_code" >&2
  exit $exit_code
}

