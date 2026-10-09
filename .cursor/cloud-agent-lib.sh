#!/usr/bin/env bash
# Shared helpers for Cloud Agent install and start. Not a standalone entrypoint.
set -euo pipefail

export PATH="/usr/local/node/bin:/usr/local/cargo/bin:${PATH:-/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin}"

ensure_dockerd() {
  if sudo docker info >/dev/null 2>&1; then
    sudo chmod 666 /var/run/docker.sock 2>/dev/null || true
    return 0
  fi
  sudo mkdir -p /etc/docker
  if ! pgrep -x dockerd >/dev/null 2>&1; then
    sudo setsid dockerd >/tmp/dockerd.log 2>&1 < /dev/null &
  fi
  local i
  for i in $(seq 1 90); do
    if sudo docker info >/dev/null 2>&1; then
      sudo chmod 666 /var/run/docker.sock 2>/dev/null || true
      return 0
    fi
    sleep 1
  done
  echo "dockerd failed to start" >&2
  sudo tail -n 100 /tmp/dockerd.log >&2 || true
  return 1
}

port_listening() {
  local port="$1"
  ss -ltn | grep -qE ":${port}\\b"
}
