# syntax=docker/dockerfile:1
# Build: docker build -f apps/driver-portal/Dockerfile -t pcd-driver .

FROM node:22-alpine AS base
RUN corepack enable
WORKDIR /app

FROM base AS deps
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/driver-portal/package.json ./apps/driver-portal/
COPY packages/config/package.json ./packages/config/
COPY packages/maps/package.json ./packages/maps/
RUN pnpm install --frozen-lockfile --filter @porterchain/driver-portal...

FROM base AS builder
COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/apps/driver-portal/node_modules ./apps/driver-portal/node_modules
COPY --from=deps /app/packages/maps/node_modules ./packages/maps/node_modules
COPY . .
ARG NEXT_PUBLIC_SITE_URL=https://driver.porterchain.com
ARG NEXT_PUBLIC_PORTERCHAIN_API_URL=https://api.porterchain.com
ARG NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
ARG NEXT_PUBLIC_GOOGLE_MAPS_API_KEY
ARG NEXT_PUBLIC_WEBSITE_URL=https://porterchain.com
ARG NEXT_PUBLIC_MERCHANT_PORTAL_URL=https://merchant.porterchain.com
ARG NEXT_PUBLIC_CUSTOMER_PORTAL_URL=https://customer.porterchain.com
ARG NEXT_PUBLIC_ADMIN_URL=https://admin.porterchain.com
ENV NEXT_PUBLIC_SITE_URL=$NEXT_PUBLIC_SITE_URL
ENV NEXT_PUBLIC_PORTERCHAIN_API_URL=$NEXT_PUBLIC_PORTERCHAIN_API_URL
ENV NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=$NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
ENV NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=$NEXT_PUBLIC_GOOGLE_MAPS_API_KEY
ENV NEXT_PUBLIC_WEBSITE_URL=$NEXT_PUBLIC_WEBSITE_URL
ENV NEXT_PUBLIC_MERCHANT_PORTAL_URL=$NEXT_PUBLIC_MERCHANT_PORTAL_URL
ENV NEXT_PUBLIC_CUSTOMER_PORTAL_URL=$NEXT_PUBLIC_CUSTOMER_PORTAL_URL
ENV NEXT_PUBLIC_ADMIN_URL=$NEXT_PUBLIC_ADMIN_URL
RUN pnpm --filter @porterchain/driver-portal build

FROM base AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV PORT=3003
RUN addgroup --system --gid 1001 nodejs && adduser --system --uid 1001 nextjs
COPY --from=builder /app/apps/driver-portal/public ./apps/driver-portal/public
COPY --from=builder --chown=nextjs:nodejs /app/apps/driver-portal/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/apps/driver-portal/.next/static ./apps/driver-portal/.next/static
USER nextjs
EXPOSE 3003
CMD ["node", "apps/driver-portal/server.js"]
