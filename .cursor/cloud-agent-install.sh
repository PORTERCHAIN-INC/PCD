#!/usr/bin/env bash
# Idempotent Cloud Agent install: Node 24.18, Python 3.14.6, Docker engine,
# pnpm workspace, API virtualenv, and local env files. Does not start servers.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# shellcheck disable=SC1091
source "$ROOT/.cursor/cloud-agent-lib.sh"

export DEBIAN_FRONTEND=noninteractive

sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
  -o Dpkg::Options::=--force-confdef \
  -o Dpkg::Options::=--force-confold \
  ca-certificates \
  curl \
  xz-utils \
  git \
  build-essential \
  pkg-config \
  iproute2 \
  docker.io \
  docker-compose-v2 \
  fuse-overlayfs \
  iptables

if [[ -x /usr/sbin/iptables-legacy ]]; then
  sudo update-alternatives --set iptables /usr/sbin/iptables-legacy || true
  sudo update-alternatives --set ip6tables /usr/sbin/ip6tables-legacy || true
fi

sudo mkdir -p /etc/docker /usr/local/cargo/bin
sudo tee /etc/docker/daemon.json >/dev/null <<'EOF'
{
  "storage-driver": "fuse-overlayfs",
  "iptables": true,
  "ip6tables": false
}
EOF

NODE_VERSION=24.18.0
NODE_PREFIX=/usr/local/node
if ! "${NODE_PREFIX}/bin/node" -v 2>/dev/null | grep -qx "v${NODE_VERSION}"; then
  tmp="$(mktemp -d)"
  curl -fsSL "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64.tar.xz" \
    | tar -xJ -C "$tmp"
  sudo rm -rf "$NODE_PREFIX"
  sudo mv "$tmp/node-v${NODE_VERSION}-linux-x64" "$NODE_PREFIX"
  rm -rf "$tmp"
fi

for b in node npm npx corepack; do
  sudo ln -sfn "${NODE_PREFIX}/bin/${b}" "/usr/local/bin/${b}"
  sudo ln -sfn "${NODE_PREFIX}/bin/${b}" "/usr/local/cargo/bin/${b}"
done

corepack enable
corepack prepare pnpm@11.10.0 --activate
# package.json dev scripts use bash `source`. Ubuntu /bin/sh is dash.
pnpm config set script-shell /bin/bash
if [[ -x "${NODE_PREFIX}/bin/pnpm" ]]; then
  sudo ln -sfn "${NODE_PREFIX}/bin/pnpm" /usr/local/bin/pnpm
  sudo ln -sfn "${NODE_PREFIX}/bin/pnpm" /usr/local/cargo/bin/pnpm
fi

if [[ ! -x "${HOME}/.local/bin/uv" ]]; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi
sudo ln -sfn "${HOME}/.local/bin/uv" /usr/local/bin/uv
sudo ln -sfn "${HOME}/.local/bin/uv" /usr/local/cargo/bin/uv
uv python install 3.14.6
PY314="$(uv python find 3.14.6)"
sudo ln -sfn "$PY314" /usr/local/bin/python3.14
sudo ln -sfn "$PY314" /usr/local/cargo/bin/python3.14
sudo ln -sfn "$PY314" /usr/local/cargo/bin/python3
sudo ln -sfn "$PY314" /usr/local/cargo/bin/python

pnpm install --frozen-lockfile

if [[ ! -x apps/api/.venv/bin/python ]] || ! apps/api/.venv/bin/python -c 'import sys; raise SystemExit(0 if sys.version_info[:3] == (3, 14, 6) else 1)'; then
  uv venv --python 3.14.6 apps/api/.venv --clear --seed
fi
(
  cd apps/api
  uv pip install --python .venv/bin/python -r requirements.txt 'pytest>=8.3.0' 'pytest-asyncio>=0.24.0'
)

copy_env() {
  local src="$1"
  local dest="$2"
  if [[ ! -f "$dest" ]]; then
    cp "$src" "$dest"
  fi
}

copy_env env/api.env.example apps/api/.env
if grep -q '^CLERK_DEV_BYPASS=false' apps/api/.env; then
  sed -i 's/^CLERK_DEV_BYPASS=false/CLERK_DEV_BYPASS=true/' apps/api/.env
fi
copy_env env/website.env.example website/.env.local
if grep -q '^NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=$' website/.env.local; then
  sed -i 's/^NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=$/NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=ci-placeholder-key/' website/.env.local
fi
copy_env env/merchant-portal.env.example apps/merchant-portal/.env.local
copy_env env/admin.env.example apps/admin/.env.local
copy_env env/driver-portal.env.example apps/driver-portal/.env.local
copy_env env/customer-portal.env.example apps/customer/.env.local

ensure_dockerd
sudo docker compose -f infrastructure/docker/docker-compose.yml --profile core pull

echo "install ok: node $(node -v) pnpm $(pnpm -v) python $(apps/api/.venv/bin/python --version)"
