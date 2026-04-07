#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Please run as root."
  exit 1
fi

APP_DIR="${STABLEGPU_APP_DIR:-/opt/stablegpu/repo}"
VENV_DIR="${STABLEGPU_VENV_DIR:-/opt/stablegpu/venv}"
DOMAIN="${STABLEGPU_DOMAIN:-}"
PUBLIC_URL="${STABLEGPU_PUBLIC_URL:-}"
API_BIND_HOST="${STABLEGPU_API_BIND_HOST:-127.0.0.1}"
API_BIND_PORT="${STABLEGPU_API_BIND_PORT:-8000}"
WEB_BIND_HOST="${STABLEGPU_WEB_BIND_HOST:-127.0.0.1}"
WEB_BIND_PORT="${STABLEGPU_WEB_BIND_PORT:-3010}"
SYSTEMD_ENV_FILE="${STABLEGPU_SYSTEMD_ENV_FILE:-${APP_DIR}/.env}"
SERVICE_PREFIX="${STABLEGPU_SERVICE_PREFIX:-stablegpu}"
NGINX_SITE_NAME="${STABLEGPU_NGINX_SITE_NAME:-stablegpu}"
WORKER_LIMIT="${STABLEGPU_WORKER_LIMIT:-5}"
WORKER_SLEEP_SECONDS="${STABLEGPU_WORKER_SLEEP_SECONDS:-2}"

if [[ -z "${DOMAIN}" ]]; then
  echo "Missing required env: STABLEGPU_DOMAIN"
  exit 1
fi

if [[ -z "${PUBLIC_URL}" ]]; then
  PUBLIC_URL="http://${DOMAIN}"
fi

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing command: $1"
    exit 1
  fi
}

if command -v apt-get >/dev/null 2>&1; then
  apt-get update
  DEBIAN_FRONTEND=noninteractive apt-get install -y python3-venv python3-pip nginx
fi

need_cmd python3
need_cmd npm
need_cmd systemctl
need_cmd nginx

if [[ ! -d "${APP_DIR}" ]]; then
  echo "App directory does not exist: ${APP_DIR}"
  exit 1
fi

mkdir -p "${APP_DIR}/data"
python3 -m venv "${VENV_DIR}"
"${VENV_DIR}/bin/pip" install --upgrade pip
"${VENV_DIR}/bin/pip" install -r "${APP_DIR}/apps/api/requirements.txt" -r "${APP_DIR}/apps/worker/requirements.txt"

pushd "${APP_DIR}/apps/web" >/dev/null
if [[ -f package-lock.json ]]; then
  npm ci
else
  npm install
fi
NEXT_PUBLIC_API_BASE_URL="${PUBLIC_URL}" npm run build
popd >/dev/null

if [[ ! -f "${SYSTEMD_ENV_FILE}" ]]; then
  cat > "${SYSTEMD_ENV_FILE}" <<EOF
STABLEGPU_DATABASE_URL=sqlite:///${APP_DIR}/data/stablegpu.db
STABLEGPU_API_SECRET_KEY=change-me-before-production
STABLEGPU_ACCESS_TOKEN_EXPIRE_MINUTES=1440
STABLEGPU_CORS_ORIGINS=["${PUBLIC_URL}"]
STABLEGPU_PROVIDER_MARKETPLACE_ADAPTER=database_mock
STABLEGPU_PROVIDER_MARKETPLACE_NAME=mock-aggregator
STABLEGPU_ENABLE_LOCAL_EXECUTOR=false
STABLEGPU_VAST_AI_OFFERS_PATH=/bundles/
EOF
  chmod 600 "${SYSTEMD_ENV_FILE}"
fi

cat > "/etc/systemd/system/${SERVICE_PREFIX}-api.service" <<EOF
[Unit]
Description=StableGPU FastAPI Service
After=network.target

[Service]
Type=simple
WorkingDirectory=${APP_DIR}
EnvironmentFile=${SYSTEMD_ENV_FILE}
Environment=PYTHONUNBUFFERED=1
ExecStart=${VENV_DIR}/bin/uvicorn apps.api.app.main:app --host ${API_BIND_HOST} --port ${API_BIND_PORT}
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

cat > "/etc/systemd/system/${SERVICE_PREFIX}-web.service" <<EOF
[Unit]
Description=StableGPU Next.js Web Service
After=network.target ${SERVICE_PREFIX}-api.service

[Service]
Type=simple
WorkingDirectory=${APP_DIR}/apps/web
Environment=NODE_ENV=production
Environment=NEXT_PUBLIC_API_BASE_URL=${PUBLIC_URL}
ExecStart=/usr/bin/npm run start -- --hostname ${WEB_BIND_HOST} --port ${WEB_BIND_PORT}
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

cat > "/etc/systemd/system/${SERVICE_PREFIX}-worker.service" <<EOF
[Unit]
Description=StableGPU Worker Loop Service
After=network.target ${SERVICE_PREFIX}-api.service

[Service]
Type=simple
WorkingDirectory=${APP_DIR}
EnvironmentFile=${SYSTEMD_ENV_FILE}
ExecStart=/bin/bash -lc 'while true; do ${VENV_DIR}/bin/python -m apps.worker.worker.main --limit ${WORKER_LIMIT} || true; sleep ${WORKER_SLEEP_SECONDS}; done'
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

cat > "/etc/nginx/sites-available/${NGINX_SITE_NAME}" <<EOF
server {
    listen 80;
    server_name ${DOMAIN};

    client_max_body_size 30m;

    location /api/ {
        proxy_pass http://${API_BIND_HOST}:${API_BIND_PORT};
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location = /docs {
        proxy_pass http://${API_BIND_HOST}:${API_BIND_PORT}/docs;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location = /openapi.json {
        proxy_pass http://${API_BIND_HOST}:${API_BIND_PORT}/openapi.json;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location / {
        proxy_pass http://${WEB_BIND_HOST}:${WEB_BIND_PORT};
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

ln -sf "/etc/nginx/sites-available/${NGINX_SITE_NAME}" "/etc/nginx/sites-enabled/${NGINX_SITE_NAME}"
nginx -t

systemctl daemon-reload
systemctl enable --now "${SERVICE_PREFIX}-api.service"
systemctl enable --now "${SERVICE_PREFIX}-web.service"
systemctl enable --now "${SERVICE_PREFIX}-worker.service"
systemctl restart nginx

echo ""
echo "Deployment completed."
echo "Public URL: ${PUBLIC_URL}"
echo "Health URL: ${PUBLIC_URL}/api/health"
echo "Docs URL: ${PUBLIC_URL}/docs"
