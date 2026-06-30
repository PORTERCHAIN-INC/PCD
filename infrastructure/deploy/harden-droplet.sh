#!/usr/bin/env bash
#
# Baseline security hardening for the Porterchain deploy droplet.
# Idempotent — safe to re-run. Run as root:
#
#   ssh root@<droplet-ip> 'bash -s' < infrastructure/deploy/harden-droplet.sh
#
# Applies:
#   - UFW firewall (deny inbound except 22/80/443)
#   - fail2ban (SSH brute-force protection)
#   - unattended-upgrades (automatic security patches)
#   - SSH hardening (key-only auth, no root password login)

set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

echo "==> Installing security packages"
apt-get update -y
apt-get install -y ufw fail2ban unattended-upgrades apt-listchanges

echo "==> Firewall (UFW)"
ufw allow OpenSSH || ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw default deny incoming
ufw default allow outgoing
ufw --force enable

echo "==> fail2ban SSH jail"
cat > /etc/fail2ban/jail.local <<'EOF'
[DEFAULT]
bantime  = 1h
findtime = 10m
maxretry = 5
backend  = systemd

[sshd]
enabled = true
port    = ssh
EOF
systemctl enable --now fail2ban
systemctl restart fail2ban

echo "==> Automatic security updates"
cat > /etc/apt/apt.conf.d/20auto-upgrades <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
EOF
cat > /etc/apt/apt.conf.d/52unattended-upgrades-local <<'EOF'
Unattended-Upgrade::Automatic-Reboot "false";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
EOF
systemctl enable --now unattended-upgrades

echo "==> SSH hardening (key-only auth)"
mkdir -p /etc/ssh/sshd_config.d
cat > /etc/ssh/sshd_config.d/99-porterchain-hardening.conf <<'EOF'
# Managed by infrastructure/deploy/harden-droplet.sh
PermitRootLogin prohibit-password
PasswordAuthentication no
KbdInteractiveAuthentication no
ChallengeResponseAuthentication no
PubkeyAuthentication yes
X11Forwarding no
MaxAuthTries 4
LoginGraceTime 30
EOF
# Validate config before reloading so we never lock ourselves out.
sshd -t
systemctl reload ssh || systemctl reload sshd

echo
echo "==> Hardening complete. Status:"
ufw status verbose | head -n 20
echo "--- fail2ban ---"
fail2ban-client status sshd 2>/dev/null || echo "(fail2ban warming up)"
echo "--- unattended-upgrades ---"
systemctl is-active unattended-upgrades
