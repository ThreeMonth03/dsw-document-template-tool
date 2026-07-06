#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DSW_ENV_FILE="${ROOT_DIR}/scripts/ci/dsw_env.sh"
COMPOSE_FILE="${ROOT_DIR}/.github/dsw/docker-compose.yml"

source "${DSW_ENV_FILE}"
docker compose -f "${COMPOSE_FILE}" down --volumes --remove-orphans
