#!/usr/bin/env bash
#
# Deploy the ChronoLog backend to the Google Cloud VM.
#
# Flow: build the image -> push to Docker Hub -> bump the tag in docker-compose.yml
#       -> copy the compose file to the VM -> pull + restart the container there.
#
# Config (host, user, paths, image) lives in scripts/.env.deploy, which is GITIGNORED.
# Copy scripts/.env.deploy.example to scripts/.env.deploy and fill it in once.
#
# Usage:
#   scripts/deploy-backend.sh <version>      e.g. scripts/deploy-backend.sh v1.0.2
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$SCRIPT_DIR/.env.deploy"
COMPOSE="$REPO_ROOT/docker-compose.yml"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: $ENV_FILE not found." >&2
  echo "       Copy scripts/.env.deploy.example to scripts/.env.deploy and fill it in." >&2
  exit 1
fi
# shellcheck disable=SC1090
set -a; source "$ENV_FILE"; set +a

VERSION="${1:-}"
if [[ -z "$VERSION" ]]; then
  echo "Usage: $0 <version>    e.g. $0 v1.0.2" >&2
  exit 1
fi

: "${IMAGE:?set IMAGE in .env.deploy (e.g. mukund146/chronologbackend)}"
: "${VM_HOST:?set VM_HOST in .env.deploy (the VM external IP or hostname)}"
: "${VM_USER:?set VM_USER in .env.deploy}"
: "${VM_PATH:?set VM_PATH in .env.deploy (dir on the VM holding docker-compose.yml + backend/.env)}"

SSH_OPTS=()
[[ -n "${SSH_KEY:-}" ]] && SSH_OPTS=(-i "$SSH_KEY")

FULL_IMAGE="$IMAGE:$VERSION"

echo ">> Building $FULL_IMAGE from backend/"
docker build -t "$FULL_IMAGE" "$REPO_ROOT/backend"

echo ">> Pushing $FULL_IMAGE to Docker Hub"
docker push "$FULL_IMAGE"

echo ">> Pinning local docker-compose.yml to $FULL_IMAGE (repo record of what's live)"
sed -i -E "s#(image:[[:space:]]*)${IMAGE}:.*#\1${FULL_IMAGE}#" "$COMPOSE"

# NOTE: we deliberately do NOT copy the local compose to the VM. The VM's compose uses a
# different env_file path (.env, not backend/.env); overwriting it would break the backend.
# Instead, bump the image tag inside the VM's own compose file in place, then redeploy.
echo ">> Updating image tag in the VM's docker-compose.yml and redeploying"
ssh "${SSH_OPTS[@]}" "${VM_USER}@${VM_HOST}" "
  set -e
  sed -i -E 's#(image:[[:space:]]*)${IMAGE}:.*#\1${FULL_IMAGE}#' '${VM_PATH}/docker-compose.yml'
  cd '${VM_PATH}'
  docker compose pull
  docker compose up -d
  docker image prune -f
"

echo ""
echo ">> Deployed ${FULL_IMAGE} to ${VM_HOST}"
echo ">> Don't forget to commit the docker-compose.yml tag bump so the repo records what's live."
