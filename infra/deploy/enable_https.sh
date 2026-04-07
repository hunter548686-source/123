#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Please run as root."
  exit 1
fi

DOMAIN="${STABLEGPU_DOMAIN:-}"
EMAIL="${STABLEGPU_LETSENCRYPT_EMAIL:-}"

if [[ -z "${DOMAIN}" ]]; then
  echo "Missing required env: STABLEGPU_DOMAIN"
  exit 1
fi

if [[ -z "${EMAIL}" ]]; then
  echo "Missing required env: STABLEGPU_LETSENCRYPT_EMAIL"
  exit 1
fi

if ! command -v apt-get >/dev/null 2>&1; then
  echo "This helper currently supports apt-based systems only."
  exit 1
fi

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y certbot python3-certbot-nginx

certbot --nginx --non-interactive --agree-tos --redirect -m "${EMAIL}" -d "${DOMAIN}"

nginx -t
systemctl reload nginx

echo "HTTPS enabled for ${DOMAIN}"

