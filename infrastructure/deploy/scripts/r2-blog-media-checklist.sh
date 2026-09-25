#!/usr/bin/env bash
# Cloudflare R2 blog-media bucket checklist (ops — needs CF + Doppler).
# Doppler placeholders already exist (upload-blog-to-doppler.sh). Local disk works without R2.
set -euo pipefail

cat <<'EOF'
R2 blog media — activate CDN (optional)
=======================================

Prereq: Doppler pcd/prd already has empty BLOG_MEDIA_* keys + WEBSITE_REVALIDATE_SECRET.

1. Cloudflare Dashboard → R2 → Create bucket (e.g. porterchain-blog-media)
2. Enable public access via custom domain OR r2.dev public URL
3. Create R2 API token (Object Read & Write) for that bucket
4. Doppler → pcd/prd set:
   BLOG_MEDIA_S3_ENDPOINT=https://<accountid>.r2.cloudflarestorage.com
   BLOG_MEDIA_S3_BUCKET=porterchain-blog-media
   BLOG_MEDIA_S3_ACCESS_KEY_ID=…
   BLOG_MEDIA_S3_SECRET_ACCESS_KEY=…
   BLOG_MEDIA_S3_REGION=auto
   BLOG_MEDIA_S3_PREFIX=blog-media
   BLOG_MEDIA_PUBLIC_BASE_URL=https://<cdn-host>/blog-media
   NEXT_PUBLIC_BLOG_MEDIA_CDN=https://<cdn-host>/blog-media
5. Re-deploy api + website (or sync doppler.env on droplet)
6. Admin → Blog → upload image → confirm URL uses CDN host

Until then: API serves from BLOG_MEDIA_DIR (local disk) — intentional default.
See docs/WEBSITE_PAGE_PLAYBOOK.md § Blog media.
EOF
