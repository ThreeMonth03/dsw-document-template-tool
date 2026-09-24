# CI MinIO image repair (2026-09-14)

The scheduled run 34782675635 failed before DSW startup: Docker Hub denied
pulls of `minio/minio` and `minio/mc`. This is independent of template rendering.

Use the official Quay repositories documented by the
[MinIO container guide](https://github.com/minio/minio/blob/master/docs/docker/README.md)
and [MinIO Client build script](https://github.com/minio/mc/blob/master/docker-buildx.sh).
The server stays at RELEASE.2025-05-24T17-08-30Z. The client is pinned to
RELEASE.2025-05-21T01-59-54Z instead of `latest`. Both default image references
include the multi-platform manifest digest verified with `docker buildx imagetools inspect`.

`MINIO_VERSION` and `MINIO_MC_VERSION` remain explicit diagnostic overrides for
tags (or tag@digest) under the Quay repositories. Updating them requires a new
storage/bootstrap and DSW 4.26/4.30 render regression run. This does not establish
production security suitability for these older images or alter production storage.

The fix branch's push runs offline checks and both DSW runtime jobs, but does
not execute scaffold release publishing. The master schedule will only adopt
the fix after a separately approved merge; dispatching the master workflow has
release/PR side effects and is not a read-only verification step.
