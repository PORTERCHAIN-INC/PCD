# syntax=docker/dockerfile:1
# Build: docker build -f apps/merchant-portal/Dockerfile -t pcd-merchant .

FROM node:24-alpine AS base
RUN corepack enable
WORKDIR /app

FROM base AS deps
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/merchant-portal/package.json ./apps/merchant-portal/
COPY packages/config/package.json ./packages/config/
COPY packages/maps/package.json ./packages/maps/
RUN pnpm install --frozen-lockfile --filter @porterchain/merchant-portal...

FROM base AS builder
COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/apps/merchant-portal/node_modules ./apps/merchant-portal/node_modules
COPY --from=deps /app/packages/config/node_modules ./packages/config/node_modules
COPY --from=deps /app/packages/maps/node_modules ./packages/maps/node_modules
COPY . .
ARG NEXT_PUBLIC_SITE_URL=https://merchant.porterchain.com
ARG NEXT_PUBLIC_PORTERCHAIN_API_URL=https://api.porterchain.com
ARG NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
ARG NEXT_PUBLIC_GOOGLE_MAPS_API_KEY
ARG NEXT_PUBLIC_SENTRY_DSN
ARG NEXT_PUBLIC_APP_ENV=production
ENV NEXT_PUBLIC_SITE_URL=$NEXT_PUBLIC_SITE_URL
ENV NEXT_PUBLIC_PORTERCHAIN_API_URL=$NEXT_PUBLIC_PORTERCHAIN_API_URL
ENV NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=$NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
ENV NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=$NEXT_PUBLIC_GOOGLE_MAPS_API_KEY
ENV NEXT_PUBLIC_SENTRY_DSN=$NEXT_PUBLIC_SENTRY_DSN
ENV NEXT_PUBLIC_APP_ENV=$NEXT_PUBLIC_APP_ENV
RUN pnpm --filter @porterchain/merchant-portal build

FROM base AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV PORT=3001
RUN addgroup --system --gid 1001 nodejs && adduser --system --uid 1001 nextjs
COPY --from=builder /app/apps/merchant-portal/public ./apps/merchant-portal/public
COPY --from=builder --chown=nextjs:nodejs /app/apps/merchant-portal/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/apps/merchant-portal/.next/static ./apps/merchant-portal/.next/static
USER nextjs
EXPOSE 3001
CMD ["node", "apps/merchant-portal/server.js"]
