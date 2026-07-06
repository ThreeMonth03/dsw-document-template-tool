#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="${ROOT_DIR}/.github/dsw/docker-compose.yml"
CONFIG_DIR="${ROOT_DIR}/.github/dsw/config"
APPLICATION_CONFIG="${CONFIG_DIR}/application.yml"
PRIVATE_KEY="${CONFIG_DIR}/jwtRS256.key"
DSW_CI_API_PORT="${DSW_CI_API_PORT:-3000}"
DSW_API_URL="${DSW_API_URL:-http://localhost:${DSW_CI_API_PORT}/wizard-api}"
DSW_EMAIL="${DSW_EMAIL:-albert.einstein@example.com}"
DSW_PASSWORD="${DSW_PASSWORD:-password}"
DSW_CI_MINIO_PORT="${DSW_CI_MINIO_PORT:-9000}"
DSW_STARTUP_TIMEOUT_SECONDS="${DSW_STARTUP_TIMEOUT_SECONDS:-300}"
DSW_CI_APP_SECRET="${DSW_CI_APP_SECRET:-$(openssl rand -hex 32)}"
DSW_CI_POSTGRES_USER="${DSW_CI_POSTGRES_USER:-dsw_ci}"
DSW_CI_POSTGRES_PASSWORD="${DSW_CI_POSTGRES_PASSWORD:-$(openssl rand -hex 24)}"
DSW_CI_MINIO_ROOT_USER="${DSW_CI_MINIO_ROOT_USER:-dswci}"
DSW_CI_MINIO_ROOT_PASSWORD="${DSW_CI_MINIO_ROOT_PASSWORD:-$(openssl rand -hex 24)}"

export DSW_CI_APP_SECRET
export DSW_CI_POSTGRES_USER
export DSW_CI_POSTGRES_PASSWORD
export DSW_CI_MINIO_ROOT_USER
export DSW_CI_MINIO_ROOT_PASSWORD

mkdir -p "${CONFIG_DIR}"

if [[ ! -f "${PRIVATE_KEY}" ]]; then
  openssl genrsa 4096 > "${PRIVATE_KEY}"
fi

{
  cat <<YAML
general:
  clientUrl: http://localhost:8080/wizard
  secret: ${DSW_CI_APP_SECRET}
  rsaPrivateKey: |
YAML
  sed 's/^/    /' "${PRIVATE_KEY}"
  cat <<YAML
database:
  connectionString: postgresql://${DSW_CI_POSTGRES_USER}:${DSW_CI_POSTGRES_PASSWORD}@postgres:5432/engine-wizard
s3:
  url: http://host.docker.internal:${DSW_CI_MINIO_PORT}
  username: ${DSW_CI_MINIO_ROOT_USER}
  password: ${DSW_CI_MINIO_ROOT_PASSWORD}
  bucket: engine-wizard
mail:
  enabled: false
  name: ""
  email: ""
  provider: smtp
  smtp:
    host: ""
    port:
    security: plain
    username: ""
    password: ""
YAML
} > "${APPLICATION_CONFIG}"

if ! getent hosts host.docker.internal >/dev/null 2>&1; then
  if command -v sudo >/dev/null 2>&1; then
    if ! echo "127.0.0.1 host.docker.internal" | sudo -n tee -a /etc/hosts >/dev/null; then
      echo "WARNING: could not add host.docker.internal to /etc/hosts without sudo password" >&2
    fi
  else
    echo "WARNING: host.docker.internal is not present in /etc/hosts" >&2
  fi
fi

docker compose -f "${COMPOSE_FILE}" up -d

deadline=$((SECONDS + DSW_STARTUP_TIMEOUT_SECONDS))
while (( SECONDS < deadline )); do
  login_response="$(curl -fsS \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"${DSW_EMAIL}\",\"password\":\"${DSW_PASSWORD}\",\"code\":null}" \
    "${DSW_API_URL}/tokens" 2>/dev/null || true)"
  token="$(printf '%s' "${login_response}" | python3 -c 'import json,sys; data=json.load(sys.stdin); print(data.get("token", ""))' 2>/dev/null || true)"
  if [[ -n "${token}" ]]; then
    bootstrap_response="$(curl -fsS \
      -H "Authorization: Bearer ${token}" \
      "${DSW_API_URL}/configs/bootstrap" 2>/dev/null || true)"
    if printf '%s' "${bootstrap_response}" | grep -q '"organization"'; then
      echo "DSW is ready at ${DSW_API_URL}"
      exit 0
    fi
  fi
  sleep 5
done

echo "ERROR: Timed out waiting for DSW bootstrap config at ${DSW_API_URL}" >&2
docker compose -f "${COMPOSE_FILE}" ps >&2 || true
docker compose -f "${COMPOSE_FILE}" logs --no-color --tail=200 >&2 || true
exit 1
