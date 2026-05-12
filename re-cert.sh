#!/usr/bin/bash
# Renews SSL certification.
# Paths can be overridden via env vars to support non-default deployments.

set -euo pipefail

DOMAIN="${CERT_DOMAIN:-saustinbc.com}"
LETSENCRYPT_LIVE="${LETSENCRYPT_LIVE:-/etc/letsencrypt/live/${DOMAIN}}"
SSL_DEST="${SSL_DEST:-/home/sabc/SABC/ssl}"

if [ ! -d "$LETSENCRYPT_LIVE" ]; then
    echo "❌ Let's Encrypt live dir not found: $LETSENCRYPT_LIVE" >&2
    exit 1
fi
if [ ! -d "$SSL_DEST" ]; then
    echo "❌ SSL destination dir not found: $SSL_DEST" >&2
    exit 1
fi

docker stop sabc-nginx
certbot renew --force-renewal
cp "${LETSENCRYPT_LIVE}/fullchain.pem" "${SSL_DEST}/"
cp "${LETSENCRYPT_LIVE}/privkey.pem" "${SSL_DEST}/"
docker start sabc-nginx