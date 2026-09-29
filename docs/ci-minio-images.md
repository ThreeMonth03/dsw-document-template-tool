# CI Object Storage

The isolated DSW test stack builds MinIO and its client from official GitHub
release assets. Their versions and SHA-256 checksums are pinned in
`.github/dsw/storage/Dockerfile`, together with the Debian base-image digest.
Compose builds the Linux/amd64 images locally; no MinIO registry credentials or
pre-existing local images are required.

Run `make start-ci-dsw` to build storage and start the test stack. Run
`make stop-ci-dsw` to remove the disposable stack and its data. Do not use these
test images or test credentials for production storage.

To update storage, change the release URLs and checksums in the Dockerfile and
the corresponding local image tags in `.github/dsw/docker-compose.yml`. Verify
the checksums against the official [MinIO releases](https://github.com/minio/minio/releases)
and [client releases](https://github.com/minio/mc/releases), then run the complete
DSW runtime matrix. Storage startup, bucket creation, document generation and
download must all pass before merging.
