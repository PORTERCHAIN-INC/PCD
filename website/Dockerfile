# syntax=docker/dockerfile:1

FROM node:20-alpine AS base
RUN corepack enable
WORKDIR /app

FROM base AS deps
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY website/package.json ./website/
COPY packages/config/package.json ./packages/config/
RUN pnpm install --frozen-lockfile --filter @porterchain/website...

FROM base AS builder
COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/website/node_modules ./website/node_modules
COPY . .
ARG NEXT_PUBLIC_GOOGLE_MAPS_API_KEY
ARG NEXT_PUBLIC_SITE_URL=https://porterchain.com
ARG NEXT_PUBLIC_PORTERCHAIN_API_URL=https://porterchain.com
ARG NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
ENV NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=$NEXT_PUBLIC_GOOGLE_MAPS_API_KEY
ENV NEXT_PUBLIC_SITE_URL=$NEXT_PUBLIC_SITE_URL
ENV NEXT_PUBLIC_PORTERCHAIN_API_URL=$NEXT_PUBLIC_PORTERCHAIN_API_URL
ENV NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=$NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
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
