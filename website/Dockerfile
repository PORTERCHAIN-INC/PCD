# syntax=docker/dockerfile:1

FROM node:24.18.0-alpine AS base
RUN corepack enable
WORKDIR /app

FROM base AS deps
COPY package.json pnpm-lock.yaml ./
COPY website/pnpm-workspace.docker.yaml ./pnpm-workspace.yaml
COPY website/package.json ./website/
COPY packages/auth/package.json ./packages/auth/
COPY packages/types/package.json ./packages/types/
COPY packages/config/package.json ./packages/config/
COPY packages/maps/package.json ./packages/maps/
COPY packages/ui/package.json ./packages/ui/
RUN pnpm install --frozen-lockfile --filter @porterchain/website...

FROM base AS builder
COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/website/node_modules ./website/node_modules
COPY --from=deps /app/packages/auth/node_modules ./packages/auth/node_modules
COPY --from=deps /app/packages/types/node_modules ./packages/types/node_modules
COPY --from=deps /app/packages/config/node_modules ./packages/config/node_modules
COPY --from=deps /app/packages/maps/node_modules ./packages/maps/node_modules
COPY --from=deps /app/packages/ui/node_modules ./packages/ui/node_modules
COPY package.json pnpm-lock.yaml ./
COPY website/pnpm-workspace.docker.yaml ./pnpm-workspace.yaml
COPY website ./website
COPY packages/auth ./packages/auth
COPY packages/types ./packages/types
COPY packages/config ./packages/config
COPY packages/maps ./packages/maps
COPY packages/ui ./packages/ui
ARG NEXT_PUBLIC_GOOGLE_MAPS_API_KEY
ARG NEXT_PUBLIC_SITE_URL=https://porterchain.com
# Leave empty in production so the site uses same-origin /v1/* (Caddy → API).
ARG NEXT_PUBLIC_PORTERCHAIN_API_URL=
ARG NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
ARG NEXT_PUBLIC_SENTRY_DSN
ARG NEXT_PUBLIC_APP_ENV=production
ARG NEXT_PUBLIC_ZOHO_SALESIQ_ENABLED=false
ARG NEXT_PUBLIC_ZOHO_SALESIQ_WIDGET_CODE
ARG NEXT_PUBLIC_GA_MEASUREMENT_ID
ARG NEXT_PUBLIC_GOOGLE_SITE_VERIFICATION
ARG NEXT_PUBLIC_GOOGLE_BUSINESS_PROFILE_URL
ARG NEXT_PUBLIC_GOOGLE_BUSINESS_REVIEW_URL
ARG NEXT_PUBLIC_CONTACT_PHONE
ARG NEXT_PUBLIC_MERCHANT_PORTAL_URL=https://merchant.porterchain.com
ARG NEXT_PUBLIC_ADMIN_PORTAL_URL=https://admin.porterchain.com
ARG NEXT_PUBLIC_CUSTOMER_PORTAL_URL=https://customer.porterchain.com
ARG NEXT_PUBLIC_DRIVER_PORTAL_URL=https://driver.porterchain.com
ENV NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=$NEXT_PUBLIC_GOOGLE_MAPS_API_KEY
ENV NEXT_PUBLIC_SITE_URL=$NEXT_PUBLIC_SITE_URL
ENV NEXT_PUBLIC_PORTERCHAIN_API_URL=$NEXT_PUBLIC_PORTERCHAIN_API_URL
ENV NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=$NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
ENV NEXT_PUBLIC_SENTRY_DSN=$NEXT_PUBLIC_SENTRY_DSN
ENV NEXT_PUBLIC_APP_ENV=$NEXT_PUBLIC_APP_ENV
ENV NEXT_PUBLIC_ZOHO_SALESIQ_ENABLED=$NEXT_PUBLIC_ZOHO_SALESIQ_ENABLED
ENV NEXT_PUBLIC_ZOHO_SALESIQ_WIDGET_CODE=$NEXT_PUBLIC_ZOHO_SALESIQ_WIDGET_CODE
ENV NEXT_PUBLIC_GA_MEASUREMENT_ID=$NEXT_PUBLIC_GA_MEASUREMENT_ID
ENV NEXT_PUBLIC_GOOGLE_SITE_VERIFICATION=$NEXT_PUBLIC_GOOGLE_SITE_VERIFICATION
ENV NEXT_PUBLIC_GOOGLE_BUSINESS_PROFILE_URL=$NEXT_PUBLIC_GOOGLE_BUSINESS_PROFILE_URL
ENV NEXT_PUBLIC_GOOGLE_BUSINESS_REVIEW_URL=$NEXT_PUBLIC_GOOGLE_BUSINESS_REVIEW_URL
ENV NEXT_PUBLIC_CONTACT_PHONE=$NEXT_PUBLIC_CONTACT_PHONE
ENV NEXT_PUBLIC_MERCHANT_PORTAL_URL=$NEXT_PUBLIC_MERCHANT_PORTAL_URL
ENV NEXT_PUBLIC_ADMIN_PORTAL_URL=$NEXT_PUBLIC_ADMIN_PORTAL_URL
ENV NEXT_PUBLIC_CUSTOMER_PORTAL_URL=$NEXT_PUBLIC_CUSTOMER_PORTAL_URL
ENV NEXT_PUBLIC_DRIVER_PORTAL_URL=$NEXT_PUBLIC_DRIVER_PORTAL_URL
RUN pnpm --filter @porterchain/website build

FROM base AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NODE_OPTIONS=--max-old-space-size=192
ENV PORT=3000
# Runtime never needs the Node-distribution npm CLI; remove it so Trivy does not
# fail on HIGH/CRITICAL findings inside /usr/local/lib/node_modules/npm.
# node:24.18.0-alpine ships OpenSSL 3.5.7 (CVE-2026-14456). Upgrade the two
# libs in place; do not float the Node image tag.
RUN apk add --no-cache 'libcrypto3>=3.5.8-r0' 'libssl3>=3.5.8-r0' \
  && rm -rf /usr/local/lib/node_modules/npm /usr/local/bin/npm /usr/local/bin/npx \
  && addgroup --system --gid 1001 nodejs && adduser --system --uid 1001 nextjs
COPY --from=builder /app/website/public ./website/public
COPY --from=builder --chown=nextjs:nodejs /app/website/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/website/.next/static ./website/.next/static
USER nextjs
EXPOSE 3000
CMD ["node", "website/server.js"]
