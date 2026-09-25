#!/usr/bin/env bash
# Upload blog CMS / website revalidate + optional media CDN keys to Doppler pcd/prd.
# Generates WEBSITE_REVALIDATE_SECRET when missing (shared by API + website).
# Optional BLOG_MEDIA_* / NEXT_PUBLIC_BLOG_MEDIA_CDN copied from local env when present.
# Never prints secret values.
#
# Usage:
#   bash infrastructure/deploy/scripts/upload-blog-to-doppler.sh
#   BLOG_ENV=/path/to/blog-keys.local.env bash infrastructure/deploy/scripts/upload-blog-to-doppler.sh
#
# Requires: doppler CLI + login (or DOPPLER_TOKEN)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
PROJECT="${DOPPLER_PROJECT:-pcd}"
CONFIG="${DOPPLER_CONFIG:-prd}"
BLOG_ENV="${BLOG_ENV:-$ROOT/apps/api/.env}"
WEBSITE_ENV="${WEBSITE_ENV:-$ROOT/website/.env.local}"

command -v doppler >/dev/null || {
  echo "Install Doppler CLI: brew install dopplerhq/cli/doppler" >&2
  exit 1
}

if [[ -z "${DOPPLER_TOKEN:-}" ]]; then
  doppler me >/dev/null 2>&1 || doppler login
fi

get_local() {
  local key="$1"
  local file
  for file in "$BLOG_ENV" "$WEBSITE_ENV" "$ROOT/env/api.env" "$ROOT/env/website.env"; do
    if [[ -f "$file" ]]; then
      local val
      val="$(grep -E "^${key}=" "$file" 2>/dev/null | tail -1 | cut -d= -f2- || true)"
      if [[ -n "$val" ]]; then
        printf '%s' "$val"
        return 0
      fi
    fi
  done
  return 0
}

doppler_get() {
  local key="$1"
  doppler secrets get "$key" --project "$PROJECT" --config "$CONFIG" --plain 2>/dev/null || true
}

ensure_generated() {
  local key="$1"
  local existing
  existing="$(doppler_get "$key")"
  if [[ -n "$existing" ]]; then
    echo "${key}: already set (not rotated)"
    return 0
  fi
  local local_val
  local_val="$(get_local "$key")"
  if [[ -n "$local_val" ]]; then
    doppler secrets set "${key}=${local_val}" --project "$PROJECT" --config "$CONFIG" >/dev/null
    echo "${key}: uploaded from local env"
    return 0
  fi
  local gen
  gen="$(openssl rand -hex 32)"
  doppler secrets set "${key}=${gen}" --project "$PROJECT" --config "$CONFIG" >/dev/null
  echo "${key}: generated and uploaded"
}

ensure_default() {
  local key="$1"
  local default="$2"
  local existing
  existing="$(doppler_get "$key")"
  if [[ -n "$existing" ]]; then
    echo "${key}: already set (not overwritten)"
    return 0
  fi
  local local_val
  local_val="$(get_local "$key")"
  if [[ -n "$local_val" ]]; then
    doppler secrets set "${key}=${local_val}" --project "$PROJECT" --config "$CONFIG" >/dev/null
    echo "${key}: uploaded from local env"
    return 0
  fi
  doppler secrets set "${key}=${default}" --project "$PROJECT" --config "$CONFIG" >/dev/null
  echo "${key}: set default placeholder (fill R2/CDN in Doppler when ready)"
}

upload_if_local() {
  local key="$1"
  local local_val
  local_val="$(get_local "$key")"
  if [[ -z "$local_val" ]]; then
    echo "${key}: skip (not in local env)"
    return 0
  fi
  local existing
  existing="$(doppler_get "$key")"
  if [[ -n "$existing" ]]; then
    echo "${key}: already set in Doppler (not overwritten — delete in Doppler to replace)"
    return 0
  fi
  doppler secrets set "${key}=${local_val}" --project "$PROJECT" --config "$CONFIG" >/dev/null
  echo "${key}: uploaded from local env"
}

echo "Doppler ${PROJECT}/${CONFIG} — blog CMS / revalidate / media"
ensure_generated WEBSITE_REVALIDATE_SECRET

# CDN + S3 optional — placeholders so keys exist in Doppler; real R2 values via local env or Doppler UI
ensure_default BLOG_MEDIA_PUBLIC_BASE_URL ""
ensure_default NEXT_PUBLIC_BLOG_MEDIA_CDN ""
ensure_default BLOG_MEDIA_S3_ENDPOINT ""
ensure_default BLOG_MEDIA_S3_BUCKET ""
ensure_default BLOG_MEDIA_S3_ACCESS_KEY_ID ""
ensure_default BLOG_MEDIA_S3_SECRET_ACCESS_KEY ""
ensure_default BLOG_MEDIA_S3_REGION "auto"
ensure_default BLOG_MEDIA_S3_PREFIX "blog-media"

for key in \
  BLOG_MEDIA_DIR \
  BLOG_MEDIA_PUBLIC_BASE_URL \
  NEXT_PUBLIC_BLOG_MEDIA_CDN \
  BLOG_MEDIA_S3_ENDPOINT \
  BLOG_MEDIA_S3_BUCKET \
  BLOG_MEDIA_S3_ACCESS_KEY_ID \
  BLOG_MEDIA_S3_SECRET_ACCESS_KEY
do
  upload_if_local "$key"
done

echo "Done. Deploy will stage doppler.env → droplet. Recreate api + website after deploy."
echo "When R2 is ready: set BLOG_MEDIA_S3_* + matching CDN bases in Doppler, then re-sync secrets."
