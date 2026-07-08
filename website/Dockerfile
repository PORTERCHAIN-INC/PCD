# syntax=docker/dockerfile:1

FROM node:24.18.0-alpine AS base
RUN corepack enable
WORKDIR /app

FROM base AS deps
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY website/package.json ./website/
COPY packages/config/package.json ./packages/config/
COPY packages/maps/package.json ./packages/maps/
RUN pnpm install --frozen-lockfile --filter @porterchain/website...

FROM base AS builder
COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/website/node_modules ./website/node_modules
COPY --from=deps /app/packages/config/node_modules ./packages/config/node_modules
COPY --from=deps /app/packages/maps/node_modules ./packages/maps/node_modules
COPY . .
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
RUN pnpm --filter @porterchain/website build

FROM base AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV PORT=3000
RUN addgroup --system --gid 1001 nodejs && adduser --system --uid 1001 nextjs
COPY --from=builder /app/website/public ./website/public
COPY --from=builder --chown=nextjs:nodejs /app/website/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/website/.next/static ./website/.next/static
USER nextjs
EXPOSE 3000
CMD ["node", "website/server.js"]
