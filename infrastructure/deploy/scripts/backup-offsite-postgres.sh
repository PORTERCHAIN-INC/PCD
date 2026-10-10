#!/usr/bin/env bash
# Porterchain — encrypted, off-site Postgres backup with retention (readiness audit #4).
#
#   pg_dump -Fc  ->  sha256  ->  encrypt (age or gpg)  ->  upload (rclone | aws s3 | file://)  ->  prune
#
# Runs on the droplet from systemd (porterchain-postgres-backup.timer) or cron. Configuration
# comes from the environment (EnvironmentFile=/opt/porterchain/backup.env); see
# backup.env.example and docs/runbooks/postgres-backup-restore.md.
#
# Never writes to the database. Refuses to upload unencrypted dumps.
set -euo pipefail
umask 077

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=deploy-paths.sh
source "$SCRIPT_DIR/deploy-paths.sh"

# ---- source database --------------------------------------------------------------------
# BACKUP_SOURCE=compose   -> docker compose -f $COMPOSE_FILE exec -T $POSTGRES_SERVICE pg_dump (prod default)
# BACKUP_SOURCE=container -> docker exec $BACKUP_CONTAINER pg_dump (local drills)
# BACKUP_SOURCE=url       -> pg_dump "$BACKUP_DATABASE_URL_BASE/<db>" on the host
BACKUP_SOURCE="${BACKUP_SOURCE:-compose}"
SERVICE="${POSTGRES_SERVICE:-postgres}"
DB_USER="${POSTGRES_USER:-porterchain}"
DATABASES="${BACKUP_DATABASES:-porterchain spicedb}"
BACKUP_NAME_PREFIX="${BACKUP_NAME_PREFIX:-porterchain}"

# ---- encryption -------------------------------------------------------------------------
# Preferred: AGE_RECIPIENTS_FILE (public keys; the private key is NOT on the server).
# Alternatives: GPG_RECIPIENT (public key in the server keyring) or
#               BACKUP_PASSPHRASE_FILE (gpg --symmetric AES256; keep a copy of the passphrase offline).
AGE_RECIPIENTS_FILE="${AGE_RECIPIENTS_FILE:-}"
GPG_RECIPIENT="${GPG_RECIPIENT:-}"
BACKUP_PASSPHRASE_FILE="${BACKUP_PASSPHRASE_FILE:-}"

# ---- off-site target --------------------------------------------------------------------
# OFFSITE_TARGET examples:
#   rclone:spaces:porterchain-backups/postgres     (rclone remote configured in rclone.conf)
#   s3://porterchain-backups/postgres              (aws cli; set S3_ENDPOINT_URL for Spaces/R2/B2)
#   file:///mnt/backup-volume/postgres             (drills / mounted volume)
OFFSITE_TARGET="${OFFSITE_TARGET:-}"
S3_ENDPOINT_URL="${S3_ENDPOINT_URL:-}"

# ---- retention --------------------------------------------------------------------------
LOCAL_RETENTION_DAYS="${LOCAL_RETENTION_DAYS:-3}"
OFFSITE_DAILY_DAYS="${OFFSITE_DAILY_DAYS:-14}"      # keep every backup this many days
OFFSITE_MONTHLY_MONTHS="${OFFSITE_MONTHLY_MONTHS:-12}" # plus the 1st-of-month backup this long
WORK_DIR="${BACKUP_WORK_DIR:-$BACKUP_DIR/offsite}"
HEARTBEAT_URL="${BACKUP_HEARTBEAT_URL:-}"           # optional dead-man ping (e.g. healthchecks.io)
DRY_RUN_PRUNE="${DRY_RUN_PRUNE:-0}"

log() { printf '%s %s\n' "$(date -u +%FT%TZ)" "$*" >&2; }
die() { log "ERROR: $*"; exit 1; }

[[ -n "$OFFSITE_TARGET" ]] || die "OFFSITE_TARGET is required (rclone:..., s3://..., file:///...)"
if [[ -n "$AGE_RECIPIENTS_FILE" ]]; then
  command -v age >/dev/null || die "age not installed"; [[ -s "$AGE_RECIPIENTS_FILE" ]] || die "AGE_RECIPIENTS_FILE empty/missing"
  ENC=age; ENC_EXT=age
elif [[ -n "$GPG_RECIPIENT" ]]; then
  command -v gpg >/dev/null || die "gpg not installed"; ENC=gpg-pub; ENC_EXT=gpg
elif [[ -n "$BACKUP_PASSPHRASE_FILE" ]]; then
  command -v gpg >/dev/null || die "gpg not installed"; [[ -s "$BACKUP_PASSPHRASE_FILE" ]] || die "BACKUP_PASSPHRASE_FILE empty/missing"
  ENC=gpg-sym; ENC_EXT=gpg
else
  die "No encryption configured (AGE_RECIPIENTS_FILE, GPG_RECIPIENT or BACKUP_PASSPHRASE_FILE). Refusing to ship plaintext."
fi
for db in $DATABASES; do [[ "$db" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || die "unsafe database name: $db"; done

# Single-instance lock (Linux flock; skipped where unavailable, e.g. macOS drills).
mkdir -p "$WORK_DIR"
if command -v flock >/dev/null; then
  exec 9>"$WORK_DIR/.lock"; flock -n 9 || die "another backup is running"
fi

sha256() { if command -v sha256sum >/dev/null; then sha256sum "$1" | cut -d' ' -f1; else shasum -a 256 "$1" | cut -d' ' -f1; fi; }

dump_db() { # $1=db -> stdout (custom format)
  local db="$1"
  case "$BACKUP_SOURCE" in
    compose)   docker compose -f "$COMPOSE_FILE" exec -T "$SERVICE" pg_dump -U "$DB_USER" -d "$db" -Fc --no-owner --no-acl ;;
    container) docker exec "${BACKUP_CONTAINER:?BACKUP_CONTAINER required}" pg_dump -U "$DB_USER" -d "$db" -Fc --no-owner --no-acl ;;
    url)       pg_dump "${BACKUP_DATABASE_URL_BASE:?BACKUP_DATABASE_URL_BASE required}/$db" -Fc --no-owner --no-acl ;;
    *) die "unknown BACKUP_SOURCE=$BACKUP_SOURCE" ;;
  esac
}

encrypt() { # $1=in $2=out
  case "$ENC" in
    age)     age -R "$AGE_RECIPIENTS_FILE" -o "$2" "$1" ;;
    gpg-pub) gpg --batch --yes --trust-model always -r "$GPG_RECIPIENT" -o "$2" --encrypt "$1" ;;
    gpg-sym) gpg --batch --yes --pinentry-mode loopback --passphrase-file "$BACKUP_PASSPHRASE_FILE" \
               --symmetric --cipher-algo AES256 -o "$2" "$1" ;;
  esac
}

upload() { # $1=local file
  local f="$1" name; name="$(basename "$f")"
  case "$OFFSITE_TARGET" in
    rclone:*) rclone copyto "$f" "${OFFSITE_TARGET#rclone:}/$name" ;;
    s3://*)   aws s3 cp ${S3_ENDPOINT_URL:+--endpoint-url "$S3_ENDPOINT_URL"} --only-show-errors "$f" "$OFFSITE_TARGET/$name" ;;
    file://*) mkdir -p "${OFFSITE_TARGET#file://}"; cp "$f" "${OFFSITE_TARGET#file://}/$name" ;;
    *) die "unsupported OFFSITE_TARGET: $OFFSITE_TARGET" ;;
  esac
}

remote_list() {
  case "$OFFSITE_TARGET" in
    rclone:*) rclone lsf "${OFFSITE_TARGET#rclone:}" ;;
    s3://*)   aws s3 ls ${S3_ENDPOINT_URL:+--endpoint-url "$S3_ENDPOINT_URL"} "$OFFSITE_TARGET/" | awk '{print $4}' ;;
    file://*) ls -1 "${OFFSITE_TARGET#file://}" 2>/dev/null || true ;;
  esac
}

remote_delete() {
  local name="$1"
  if [[ "$DRY_RUN_PRUNE" == "1" ]]; then log "prune (dry-run): $name"; return; fi
  case "$OFFSITE_TARGET" in
    rclone:*) rclone deletefile "${OFFSITE_TARGET#rclone:}/$name" ;;
    s3://*)   aws s3 rm ${S3_ENDPOINT_URL:+--endpoint-url "$S3_ENDPOINT_URL"} --only-show-errors "$OFFSITE_TARGET/$name" ;;
    file://*) rm -f "${OFFSITE_TARGET#file://}/$name" ;;
  esac
  log "pruned $name"
}

epoch_of_stamp() { # YYYYmmddTHHMMSSZ -> epoch (GNU, BusyBox or BSD date)
  local s="$1" plain="${1:0:4}-${1:4:2}-${1:6:2} ${1:9:2}:${1:11:2}:${1:13:2}"
  date -u -d "$plain" +%s 2>/dev/null || date -u -j -f "%Y%m%dT%H%M%SZ" "$s" +%s
}

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
NOW="$(date -u +%s)"
uploaded=0
for db in $DATABASES; do
  base="${BACKUP_NAME_PREFIX}-${db}-${STAMP}"
  raw="$WORK_DIR/$base.dump"
  log "dumping $db ($BACKUP_SOURCE)"
  dump_db "$db" >"$raw"
  [[ -s "$raw" ]] || die "empty dump for $db"
  # Validate the archive TOC before shipping (pg_restore --list reads it without a DB).
  case "$BACKUP_SOURCE" in
    compose)   docker compose -f "$COMPOSE_FILE" exec -T "$SERVICE" pg_restore --list <"$raw" >/dev/null ;;
    container) docker exec -i "$BACKUP_CONTAINER" pg_restore --list <"$raw" >/dev/null ;;
    url)       pg_restore --list "$raw" >/dev/null ;;
  esac
  sum="$(sha256 "$raw")"
  enc="$raw.$ENC_EXT"
  encrypt "$raw" "$enc"
  rm -f "$raw"
  printf '%s  %s\n' "$sum" "$base.dump" >"$WORK_DIR/$base.dump.sha256"
  upload "$enc"
  upload "$WORK_DIR/$base.dump.sha256"
  log "uploaded $(basename "$enc") ($(wc -c <"$enc" | tr -d ' ') bytes, sha256 plaintext $sum)"
  uploaded=$((uploaded + 1))
done

# ---- forensic evidence bundle (audit chain + signed checkpoint + server logs) -------------
# Tamper-evident audit export, Caddy access logs and host auth/syslog, encrypted like the dumps.
EVIDENCE="${BACKUP_EVIDENCE:-1}"
EVIDENCE_DAYS="${EVIDENCE_RETENTION_DAYS:-400}"   # >= 1 year (PIPEDA breach records: 24 months via DB)
if [[ "$EVIDENCE" == "1" && "$BACKUP_SOURCE" == "compose" ]]; then
  ev="$WORK_DIR/${BACKUP_NAME_PREFIX}-evidence-${STAMP}"
  mkdir -p "$ev"
  docker compose -f "$COMPOSE_FILE" exec -T api python -m porterchain_api.forensics_cli checkpoint >"$ev/checkpoint.json" 2>"$ev/checkpoint.err" || log "checkpoint failed (see bundle)"
  docker compose -f "$COMPOSE_FILE" exec -T api python -m porterchain_api.forensics_cli export >"$ev/audit-chain.json" || log "audit export failed"
  docker compose -f "$COMPOSE_FILE" exec -T caddy sh -c 'cd /data/logs 2>/dev/null && tar -cf - . ' >"$ev/caddy-access-logs.tar" 2>/dev/null || true
  journalctl --since "-2 days" -o short-iso-precise _SYSTEMD_UNIT=ssh.service _SYSTEMD_UNIT=sshd.service + _COMM=sudo + SYSLOG_FACILITY=10 >"$ev/auth.log" 2>/dev/null || true
  journalctl --since "-2 days" -o short-iso-precise -p warning >"$ev/system-warnings.log" 2>/dev/null || true
  timedatectl show -p NTPSynchronized -p TimeUSec >"$ev/time-sync.txt" 2>/dev/null || true
  (cd "$ev" && sha256sum ./* >SHA256SUMS 2>/dev/null || shasum -a 256 ./* >SHA256SUMS)
  tar -C "$WORK_DIR" -czf "$ev.tar.gz" "$(basename "$ev")"
  rm -rf "$ev"
  encrypt "$ev.tar.gz" "$ev.tar.gz.$ENC_EXT"
  rm -f "$ev.tar.gz"
  upload "$ev.tar.gz.$ENC_EXT"
  log "uploaded evidence bundle $(basename "$ev").tar.gz.$ENC_EXT"
  ev_cutoff=$((NOW - EVIDENCE_DAYS * 86400))
  while IFS= read -r name; do
    [[ "$name" =~ ^${BACKUP_NAME_PREFIX}-evidence-([0-9]{8}T[0-9]{6}Z)\.tar ]] || continue
    (( $(epoch_of_stamp "${BASH_REMATCH[1]}") >= ev_cutoff )) || remote_delete "$name"
  done < <(remote_list)
fi

# ---- retention: off-site ----------------------------------------------------------------
daily_cutoff=$((NOW - OFFSITE_DAILY_DAYS * 86400))
monthly_cutoff=$((NOW - OFFSITE_MONTHLY_MONTHS * 31 * 86400))
while IFS= read -r name; do
  [[ "$name" =~ ^${BACKUP_NAME_PREFIX}-evidence- ]] && continue
  [[ "$name" =~ ^${BACKUP_NAME_PREFIX}-[A-Za-z0-9_]+-([0-9]{8}T[0-9]{6}Z)\.dump ]] || continue
  stamp="${BASH_REMATCH[1]}"; ts="$(epoch_of_stamp "$stamp")"
  (( ts >= daily_cutoff )) && continue
  if [[ "${stamp:6:2}" == "01" ]] && (( ts >= monthly_cutoff )); then continue; fi
  remote_delete "$name"
done < <(remote_list)

# ---- retention: local work dir ----------------------------------------------------------
find "$WORK_DIR" -maxdepth 1 -type f -name "${BACKUP_NAME_PREFIX}-*" -mtime +"$LOCAL_RETENTION_DAYS" -delete 2>/dev/null || true

log "backup complete: $uploaded database(s) -> $OFFSITE_TARGET"
if [[ -n "$HEARTBEAT_URL" ]]; then curl -fsS -m 10 --retry 3 "$HEARTBEAT_URL" >/dev/null || log "heartbeat ping failed"; fi
