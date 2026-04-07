#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Please run as root."
  exit 1
fi

ENV_FILE="${STABLEGPU_SYSTEMD_ENV_FILE:-/opt/stablegpu/repo/.env}"
SERVICE_PREFIX="${STABLEGPU_SERVICE_PREFIX:-stablegpu}"
VAST_KEY="${STABLEGPU_VAST_AI_API_KEY:-}"
RUNPOD_KEY="${STABLEGPU_RUNPOD_API_KEY:-}"
VAST_BASE_URL="${STABLEGPU_VAST_AI_BASE_URL:-https://console.vast.ai/api/v0}"
RUNPOD_BASE_URL="${STABLEGPU_RUNPOD_BASE_URL:-https://rest.runpod.io/v1}"

if [[ -z "${VAST_KEY}" ]]; then
  echo "Missing required env: STABLEGPU_VAST_AI_API_KEY"
  exit 1
fi

if [[ -z "${RUNPOD_KEY}" ]]; then
  echo "Missing required env: STABLEGPU_RUNPOD_API_KEY"
  exit 1
fi

mkdir -p "$(dirname "${ENV_FILE}")"
if [[ ! -f "${ENV_FILE}" ]]; then
  touch "${ENV_FILE}"
fi

cp "${ENV_FILE}" "${ENV_FILE}.bak.$(date +%Y%m%d%H%M%S)"

upsert_env() {
  local key="$1"
  local value="$2"
  python3 - "${ENV_FILE}" "${key}" "${value}" <<'PY'
import sys
from pathlib import Path

env_path = Path(sys.argv[1])
key = sys.argv[2]
value = sys.argv[3]

lines = env_path.read_text(encoding="utf-8").splitlines()
updated = []
found = False
prefix = f"{key}="

for line in lines:
    if line.startswith(prefix):
        updated.append(f"{key}={value}")
        found = True
    else:
        updated.append(line)

if not found:
    updated.append(f"{key}={value}")

env_path.write_text("\n".join(updated) + "\n", encoding="utf-8")
PY
}

upsert_env "STABLEGPU_PROVIDER_MARKETPLACE_ADAPTER" "multi_provider_live"
upsert_env "STABLEGPU_PROVIDER_MARKETPLACE_NAME" "vast-runpod-live"
upsert_env "STABLEGPU_VAST_AI_BASE_URL" "${VAST_BASE_URL}"
upsert_env "STABLEGPU_VAST_AI_OFFERS_PATH" "/bundles/"
upsert_env "STABLEGPU_VAST_AI_API_KEY" "${VAST_KEY}"
upsert_env "STABLEGPU_RUNPOD_BASE_URL" "${RUNPOD_BASE_URL}"
upsert_env "STABLEGPU_RUNPOD_API_KEY" "${RUNPOD_KEY}"

chmod 600 "${ENV_FILE}"

systemctl restart "${SERVICE_PREFIX}-api.service" "${SERVICE_PREFIX}-worker.service"
systemctl --no-pager --full status "${SERVICE_PREFIX}-api.service" | head -n 25
systemctl --no-pager --full status "${SERVICE_PREFIX}-worker.service" | head -n 25

echo ""
echo "Switched to multi_provider_live adapter."
echo "Env file: ${ENV_FILE}"
