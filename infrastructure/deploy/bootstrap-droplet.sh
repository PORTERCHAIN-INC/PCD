#!/usr/bin/env bash
#
# One-time provisioning for the Porterchain deploy droplet (Digital Ocean).
# Run this once on a fresh Ubuntu droplet as root:
#
#   ssh root@<droplet-ip> 'bash -s' < infrastructure/deploy/bootstrap-droplet.sh
#
# It installs Docker, opens the web/SSH ports, and prepares the host so the
# GitHub Actions "Deploy" workflow can pull images from GHCR and run them.

set -euo pipefail

echo "==> Updating apt and installing prerequisites"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y ca-certificates curl gnupg ufw

if ! command -v docker >/dev/null 2>&1; then
  echo "==> Installing Docker Engine"
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  . /etc/os-release
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
else
  echo "==> Docker already installed: $(docker --version)"
fi

systemctl enable --now docker

echo "==> Configuring firewall (UFW)"
ufw allow OpenSSH || ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
ufw status verbose

echo
echo "==> Bootstrap complete."
echo "Next steps:"
echo "  1. Add the deploy SSH public key to ~/.ssh/authorized_keys for the deploy user."
echo "  2. Configure the GitHub repo secrets (see infrastructure/deploy/README.md)."
echo "  3. Push to main (or run the Deploy workflow manually) to ship the website."
