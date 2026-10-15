# ==============================================================================
# HAMSA OSINT ENTERPRISE FRONTEND DOCKERFILE
# Base OS: Debian 12 (Bookworm Slim) Node.js 20 LTS
# ==============================================================================

FROM node:20-bookworm-slim AS base
WORKDIR /app

# Dependencies Stage
FROM base AS deps
COPY package.json package-lock.json ./
RUN npm ci

# Builder Stage
FROM base AS builder
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# Runner Stage
FROM base AS runner
ENV NODE_ENV=production \
    PORT=3000 \
    NEXT_TELEMETRY_DISABLED=1

COPY --from=builder /app/package.json ./
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public

EXPOSE 3000

CMD ["npm", "start"]
