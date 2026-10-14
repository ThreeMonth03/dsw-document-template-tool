FROM debian:bookworm-slim@sha256:3783cc01769c7b2b1b83a5c5ad96c815348e28ed7da68e2e3687004faa906251 AS base

FROM base AS minio
ADD --checksum=sha256:9d59640ae14a8b9bf74c5a85ff6a86178fb7ac7bef92eba03d8016e6bb527a10 \
    https://github.com/minio/minio/releases/download/RELEASE.2025-05-24T17-08-30Z/minio_20250524170830.0.0_amd64.deb /tmp/minio.deb
RUN dpkg-deb --extract /tmp/minio.deb /tmp/minio-package \
    && install /tmp/minio-package/usr/local/bin/minio /usr/local/bin/minio \
    && rm -rf /tmp/minio.deb /tmp/minio-package \
    && minio --version
ENTRYPOINT ["/usr/local/bin/minio"]

FROM base AS mc
ADD --chmod=0755 --checksum=sha256:fb11c542a9d781fb228de1126c267a7933e98bee831654462fb352d5c9e94d24 \
    https://github.com/minio/mc/releases/download/RELEASE.2025-05-21T01-59-54Z/mc.linux-amd64.RELEASE.2025-05-21T01-59-54Z /usr/local/bin/mc
RUN mc --version
ENTRYPOINT ["/usr/local/bin/mc"]
