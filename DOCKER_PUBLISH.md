# Docker Publish Guide

Instructions to build and publish the Docker image to Docker Hub.

## Prerequisites

- Docker with buildx plugin installed
- Logged in to Docker Hub: `docker login`

## One-time setup: create a multi-arch builder

```bash
docker buildx create --name multiarch --driver docker-container --use
docker buildx inspect multiarch --bootstrap
```

## Build and push

Replace `<VERSION>` with the target version (e.g. `1.1.3`).

```bash
docker buildx build \
  --builder multiarch \
  --platform linux/amd64,linux/arm64 \
  -t daninotfound/vinted-notifications:<VERSION> \
  -t daninotfound/vinted-notifications:latest \
  --push .
```

## Verify

```bash
# Check the tags on Docker Hub
docker buildx imagetools inspect daninotfound/vinted-notifications:<VERSION>
docker buildx imagetools inspect daninotfound/vinted-notifications:latest
```
