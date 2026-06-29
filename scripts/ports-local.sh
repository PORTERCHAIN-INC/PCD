#!/usr/bin/env bash
# List Porterchain local dev ports and whether each is in use.
set -euo pipefail

PORTS=(
  "3000:Website"
  "3001:Merchant portal"
  "3002:Admin platform"
  "3003:Driver web portal"
  "4200:Fleetbase console"
  "8000:Fleetbase API"
  "8001:Porterchain API"
  "8002:Valhalla"
  "8080:Nginx dev proxy"
  "1025:Mailhog SMTP"
  "8025:Mailhog UI"
  "3306:MySQL"
  "5432:PostgreSQL"
  "6379:Redis"
  "38000:Fleetbase SocketCluster"
)

printf "%-6s %-24s %s\n" "PORT" "SERVICE" "STATUS"
printf "%-6s %-24s %s\n" "----" "-------" "------"

for entry in "${PORTS[@]}"; do
  port="${entry%%:*}"
  name="${entry#*:}"
  if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    pid="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null | head -1)"
    proc="$(ps -p "$pid" -o comm= 2>/dev/null || echo "?")"
    status="IN USE (pid $pid, $proc)"
  else
    status="free"
  fi
  printf "%-6s %-24s %s\n" "$port" "$name" "$status"
done
