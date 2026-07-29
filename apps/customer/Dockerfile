# syntax=docker/dockerfile:1
# Build: docker build -f apps/customer/Dockerfile -t pcd-customer .

FROM node:24.18.0-alpine AS base
RUN corepack enable
WORKDIR /app

FROM base AS deps
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/customer/package.json ./apps/customer/
COPY packages/config/package.json ./packages/config/
COPY packages/maps/package.json ./packages/maps/
RUN pnpm install --frozen-lockfile --filter @porterchain/customer...

FROM base AS builder
COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/apps/customer/node_modules ./apps/customer/node_modules
COPY --from=deps /app/packages/config/node_modules ./packages/config/node_modules
COPY --from=deps /app/packages/maps/node_modules ./packages/maps/node_modules
COPY . .
ARG NEXT_PUBLIC_SITE_URL=https://customer.porterchain.com
ARG NEXT_PUBLIC_PORTERCHAIN_API_URL=https://api.porterchain.com
ARG NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
ARG NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
ARG NEXT_PUBLIC_CLERK_SIGN_IN_FORCE_REDIRECT_URL=/dashboard
ARG NEXT_PUBLIC_CLERK_SIGN_IN_FALLBACK_REDIRECT_URL=/dashboard
ARG NEXT_PUBLIC_GOOGLE_MAPS_API_KEY
ARG NEXT_PUBLIC_WEBSITE_URL=https://porterchain.com
ARG NEXT_PUBLIC_SENTRY_DSN
ARG NEXT_PUBLIC_APP_ENV=production
ENV NEXT_PUBLIC_SITE_URL=$NEXT_PUBLIC_SITE_URL
ENV NEXT_PUBLIC_PORTERCHAIN_API_URL=$NEXT_PUBLIC_PORTERCHAIN_API_URL
ENV NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=$NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
ENV NEXT_PUBLIC_CLERK_SIGN_IN_URL=$NEXT_PUBLIC_CLERK_SIGN_IN_URL
ENV NEXT_PUBLIC_CLERK_SIGN_IN_FORCE_REDIRECT_URL=$NEXT_PUBLIC_CLERK_SIGN_IN_FORCE_REDIRECT_URL
ENV NEXT_PUBLIC_CLERK_SIGN_IN_FALLBACK_REDIRECT_URL=$NEXT_PUBLIC_CLERK_SIGN_IN_FALLBACK_REDIRECT_URL
ENV NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=$NEXT_PUBLIC_GOOGLE_MAPS_API_KEY
ENV NEXT_PUBLIC_WEBSITE_URL=$NEXT_PUBLIC_WEBSITE_URL
ENV NEXT_PUBLIC_SENTRY_DSN=$NEXT_PUBLIC_SENTRY_DSN
ENV NEXT_PUBLIC_APP_ENV=$NEXT_PUBLIC_APP_ENV
RUN mkdir -p apps/customer/public
RUN pnpm --filter @porterchain/customer build

FROM base AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV PORT=3004
RUN addgroup --system --gid 1001 nodejs && adduser --system --uid 1001 nextjs
COPY --from=builder /app/apps/customer/public ./apps/customer/public
COPY --from=builder --chown=nextjs:nodejs /app/apps/customer/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/apps/customer/.next/static ./apps/customer/.next/static
USER nextjs
EXPOSE 3004
CMD ["node", "apps/customer/server.js"]
