#!/usr/bin/bash
# Renews the SSL certificate and syncs it into the directory nginx reads.
#
# Paths can be overridden via env vars to support non-default deployments.
#
# IMPORTANT — why the trap exists:
# This script stops nginx so certbot's standalone plugin can bind port 80.
# Any failure between the stop and the start (a certbot error, a rate limit,
# a Ctrl-C) used to abort the script under `set -e` and leave nginx stopped
# indefinitely. `restart: always` does NOT rescue this: a manual `docker stop`
# clears the restart intent, so Docker deliberately leaves the container down.
# That took saustinbc.com down for ~12 hours on 2026-08-20. nginx must come
# back up on every exit path, even a failed renewal — serving the OLD
# certificate is strictly better than serving nothing.

set -euo pipefail

DOMAIN="${CERT_DOMAIN:-saustinbc.com}"
LETSENCRYPT_LIVE="${LETSENCRYPT_LIVE:-/etc/letsencrypt/live/${DOMAIN}}"
SSL_DEST="${SSL_DEST:-/home/sabc/SABC/ssl}"
NGINX_CONTAINER="${NGINX_CONTAINER:-sabc-nginx}"

if [ ! -d "$LETSENCRYPT_LIVE" ]; then
    echo "❌ Let's Encrypt live dir not found: $LETSENCRYPT_LIVE" >&2
    exit 1
fi
if [ ! -d "$SSL_DEST" ]; then
    echo "❌ SSL destination dir not found: $SSL_DEST" >&2
    exit 1
fi

# Bring nginx back no matter how we leave this script.
nginx_back_up() {
    local rc=$?
    echo "▶️  Restarting ${NGINX_CONTAINER}..."
    if ! docker start "$NGINX_CONTAINER" >/dev/null 2>&1; then
        echo "🚨 FAILED to start ${NGINX_CONTAINER} — THE SITE IS DOWN." >&2
        echo "   Recover with: docker compose -f docker-compose.prod.yml up -d nginx" >&2
        exit 1
    fi
    if [ "$rc" -ne 0 ]; then
        echo "❌ Renewal failed (exit ${rc}); nginx is back up on the EXISTING certificate." >&2
        echo "   Check /var/log/letsencrypt/letsencrypt.log before the cert expires." >&2
    fi
}
trap nginx_back_up EXIT

echo "🛑 Stopping ${NGINX_CONTAINER} to free port 80 for certbot..."
docker stop "$NGINX_CONTAINER"

# No --force-renewal. Forcing a brand-new certificate on every run burns
# Let's Encrypt's "5 duplicate certificates per week" allowance and then
# starts erroring, which is what triggered the outage above. Plain `renew`
# is a no-op until the cert is within 30 days of expiry — safe to run daily.
# Set CERT_FORCE=1 for the rare case where you genuinely need a fresh cert.
echo "🔑 Renewing certificate for ${DOMAIN}..."
if [ "${CERT_FORCE:-0}" = "1" ]; then
    echo "   (CERT_FORCE=1 — forcing renewal; mind the rate limit)"
    certbot renew --force-renewal
else
    certbot renew
fi

# Copy unconditionally, not just when this run renewed something. certbot may
# have renewed on its own schedule (or via another hook) without anything
# updating SSL_DEST, so nginx can end up pinned to a stale cert. Re-copying
# every run keeps the two in sync.
echo "📋 Syncing certificate into ${SSL_DEST}..."
cp "${LETSENCRYPT_LIVE}/fullchain.pem" "${SSL_DEST}/"
cp "${LETSENCRYPT_LIVE}/privkey.pem" "${SSL_DEST}/"

echo "📅 Certificate now valid:"
openssl x509 -in "${SSL_DEST}/fullchain.pem" -noout -dates

# nginx restart is handled by the EXIT trap.
