#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="${ROOT_DIR}/.github/dsw/docker-compose.yml"
OUTPUT_DIR="${ROOT_DIR}/outputs/ci-dsw"

mkdir -p "${OUTPUT_DIR}"
docker compose -f "${COMPOSE_FILE}" ps > "${OUTPUT_DIR}/compose-ps.txt" || true
docker compose -f "${COMPOSE_FILE}" logs --no-color > "${OUTPUT_DIR}/compose.log" || true
