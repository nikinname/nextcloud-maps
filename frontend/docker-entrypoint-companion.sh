#!/bin/sh
set -eu

CERT_MODE="${CERT_MODE:-selfsigned}"
PUBLIC_HOSTNAME="${PUBLIC_HOSTNAME:-localhost}"
HTTPS_PORT="${HTTPS_PORT:-8443}"

export PUBLIC_HOSTNAME
export HTTPS_PORT

if [ "$CERT_MODE" = "letsencrypt" ]; then
    TLS_CERTIFICATE_PATH="/etc/letsencrypt/live/${PUBLIC_HOSTNAME}/fullchain.pem"
    TLS_CERTIFICATE_KEY_PATH="/etc/letsencrypt/live/${PUBLIC_HOSTNAME}/privkey.pem"
else
    TLS_CERTIFICATE_PATH="/etc/nginx/selfsigned/fullchain.pem"
    TLS_CERTIFICATE_KEY_PATH="/etc/nginx/selfsigned/privkey.pem"
fi

export TLS_CERTIFICATE_PATH
export TLS_CERTIFICATE_KEY_PATH

if [ ! -f "$TLS_CERTIFICATE_PATH" ] || [ ! -f "$TLS_CERTIFICATE_KEY_PATH" ]; then
    mkdir -p "$(dirname "$TLS_CERTIFICATE_PATH")" "$(dirname "$TLS_CERTIFICATE_KEY_PATH")"
    openssl req \
        -x509 \
        -nodes \
        -newkey rsa:2048 \
        -days 30 \
        -keyout "$TLS_CERTIFICATE_KEY_PATH" \
        -out "$TLS_CERTIFICATE_PATH" \
        -subj "/CN=${PUBLIC_HOSTNAME}" >/dev/null 2>&1
fi

envsubst '${PUBLIC_HOSTNAME} ${HTTPS_PORT} ${TLS_CERTIFICATE_PATH} ${TLS_CERTIFICATE_KEY_PATH}' \
    < /etc/nginx/templates/default.conf.template \
    > /etc/nginx/conf.d/default.conf

(
    while true; do
        sleep 300
        nginx -s reload >/dev/null 2>&1 || true
    done
) &

exec nginx -g "daemon off;"
