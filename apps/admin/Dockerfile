# syntax=docker/dockerfile:1
# Build: docker build -f apps/admin/Dockerfile -t pcd-admin .

FROM node:20-alpine AS base
RUN corepack enable
WORKDIR /app

FROM base AS deps
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/admin/package.json ./apps/admin/
COPY packages/ui/package.json ./packages/ui/
RUN pnpm install --frozen-lockfile --filter @porterchain/admin...

FROM base AS builder
COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/apps/admin/node_modules ./apps/admin/node_modules
COPY . .
ARG NEXT_PUBLIC_SITE_URL=https://admin.porterchain.com
ARG NEXT_PUBLIC_PORTERCHAIN_API_URL=https://api.porterchain.com
ARG NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
ARG NEXT_PUBLIC_GOOGLE_MAPS_API_KEY
ARG NEXT_PUBLIC_WEBSITE_URL=https://porterchain.com
ARG NEXT_PUBLIC_MERCHANT_PORTAL_URL=https://merchant.porterchain.com
ARG NEXT_PUBLIC_CUSTOMER_PORTAL_URL=https://customer.porterchain.com
ARG NEXT_PUBLIC_DRIVER_PORTAL_URL=https://driver.porterchain.com
ENV NEXT_PUBLIC_SITE_URL=$NEXT_PUBLIC_SITE_URL
ENV NEXT_PUBLIC_PORTERCHAIN_API_URL=$NEXT_PUBLIC_PORTERCHAIN_API_URL
ENV NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=$NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
ENV NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=$NEXT_PUBLIC_GOOGLE_MAPS_API_KEY
ENV NEXT_PUBLIC_WEBSITE_URL=$NEXT_PUBLIC_WEBSITE_URL
ENV NEXT_PUBLIC_MERCHANT_PORTAL_URL=$NEXT_PUBLIC_MERCHANT_PORTAL_URL
ENV NEXT_PUBLIC_CUSTOMER_PORTAL_URL=$NEXT_PUBLIC_CUSTOMER_PORTAL_URL
ENV NEXT_PUBLIC_DRIVER_PORTAL_URL=$NEXT_PUBLIC_DRIVER_PORTAL_URL
RUN pnpm --filter @porterchain/admin build

FROM base AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV PORT=3002
RUN addgroup --system --gid 1001 nodejs && adduser --system --uid 1001 nextjs
COPY --from=builder /app/apps/admin/public ./apps/admin/public
COPY --from=builder --chown=nextjs:nodejs /app/apps/admin/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/apps/admin/.next/static ./apps/admin/.next/static
USER nextjs
EXPOSE 3002
CMD ["node", "apps/admin/server.js"]
