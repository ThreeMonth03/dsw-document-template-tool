#!/usr/bin/env bash
# Shared ephemeral DSW stack environment.
#
# docker compose interpolates service environment variables even for `logs`
# and `down`, so every helper that touches the compose file must provide these
# values. They are intentionally runtime-only and can be overridden by callers.

if [[ -z "${DSW_CI_ENV_LOADED:-}" ]]; then
  DSW_CI_APP_SECRET="${DSW_CI_APP_SECRET:-$(openssl rand -hex 16)}"
  DSW_CI_POSTGRES_USER="${DSW_CI_POSTGRES_USER:-dsw_ci}"
  DSW_CI_POSTGRES_PASSWORD="${DSW_CI_POSTGRES_PASSWORD:-$(openssl rand -hex 24)}"
  DSW_CI_MINIO_ROOT_USER="${DSW_CI_MINIO_ROOT_USER:-dswci}"
  DSW_CI_MINIO_ROOT_PASSWORD="${DSW_CI_MINIO_ROOT_PASSWORD:-$(openssl rand -hex 24)}"

  export DSW_CI_APP_SECRET
  export DSW_CI_POSTGRES_USER
  export DSW_CI_POSTGRES_PASSWORD
  export DSW_CI_MINIO_ROOT_USER
  export DSW_CI_MINIO_ROOT_PASSWORD
  export DSW_CI_ENV_LOADED=1
fi
