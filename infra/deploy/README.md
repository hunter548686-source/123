# Self-Hosted Deployment

This folder contains reproducible deployment scripts for running StableGPU on your own Linux VPS.

## 1) Prepare code on server

```bash
mkdir -p /opt/stablegpu
git clone https://github.com/hunter548686-source/123.git /opt/stablegpu/repo
cd /opt/stablegpu/repo
```

## 2) Run install script

```bash
export STABLEGPU_DOMAIN=gpu.144.202.58.159.sslip.io
bash infra/deploy/install_linux.sh
```

Optional variables:

- `STABLEGPU_APP_DIR` (default `/opt/stablegpu/repo`)
- `STABLEGPU_VENV_DIR` (default `/opt/stablegpu/venv`)
- `STABLEGPU_PUBLIC_URL` (default `http://$STABLEGPU_DOMAIN`)
- `STABLEGPU_SYSTEMD_ENV_FILE` (default `$STABLEGPU_APP_DIR/.env`)
- `STABLEGPU_SERVICE_PREFIX` (default `stablegpu`)
- `STABLEGPU_NGINX_SITE_NAME` (default `stablegpu`)
- `STABLEGPU_API_BIND_PORT` (default `8000`)
- `STABLEGPU_WEB_BIND_PORT` (default `3010`)

## 3) Enable HTTPS (optional but recommended)

Prerequisites:

- Domain DNS points to your VPS.
- Port 80/443 is open.

```bash
export STABLEGPU_DOMAIN=your-domain.com
export STABLEGPU_LETSENCRYPT_EMAIL=you@example.com
bash infra/deploy/enable_https.sh
```

## 4) Service operations

```bash
systemctl status stablegpu-api.service
systemctl status stablegpu-web.service
systemctl status stablegpu-worker.service
systemctl restart stablegpu-api.service stablegpu-web.service stablegpu-worker.service
journalctl -u stablegpu-api.service -n 200 --no-pager
```

## 5) Switch from mock to real providers

```bash
export STABLEGPU_VAST_AI_API_KEY=your_vast_key
export STABLEGPU_RUNPOD_API_KEY=your_runpod_key
bash infra/deploy/switch_to_live_adapter.sh
```

This will:

- set `STABLEGPU_PROVIDER_MARKETPLACE_ADAPTER=multi_provider_live`
- set provider contract paths:
  - Vast.ai: `bundles -> asks -> instances`
  - Runpod: `GraphQL gpuTypes + REST pods`
- inject Vast.ai and Runpod API keys into env file
- set `STABLEGPU_RUNPOD_GRAPHQL_URL` and `STABLEGPU_PROVIDER_READY_STATE_IS_SUCCESS=true`
- restart `stablegpu-api.service` and `stablegpu-worker.service`

Preflight check before/after switching:

```bash
python3 infra/deploy/provider_preflight.py
```

## 6) Environment file

`install_linux.sh` creates a minimal `.env` only if none exists.

For production, you should edit:

- `STABLEGPU_API_SECRET_KEY`
- `STABLEGPU_PROVIDER_MARKETPLACE_ADAPTER`
- `STABLEGPU_VAST_AI_API_KEY`
- `STABLEGPU_RUNPOD_API_KEY`
- CORS and model settings
