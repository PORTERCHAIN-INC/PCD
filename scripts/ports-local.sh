#!/usr/bin/env bash
# List Porterchain local dev ports and production subdomain mapping.
set -euo pipefail

PORTS=(
  "3000:porterchain.com (website)"
  "3001:merchant.porterchain.com"
  "3002:admin.porterchain.com"
  "3003:driver.porterchain.com"
  "3004:customer.porterchain.com"
  "4200:fleetbase console (optional)"
  "8000:fleetbase API (optional)"
  "8001:api.porterchain.com (Porterchain API)"
  "8002:Valhalla (optional)"
  "8080:Nginx dev proxy"
  "1025:Mailhog SMTP"
  "8025:Mailhog UI"
  "3306:MySQL"
  "5432:PostgreSQL"
  "6379:Redis"
  "38000:Fleetbase SocketCluster"
)

printf "%-6s %-36s %s\n" "PORT" "PRODUCTION / SERVICE" "STATUS"
printf "%-6s %-36s %s\n" "----" "--------------------" "------"

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
  printf "%-6s %-36s %s\n" "$port" "$name" "$status"
done
