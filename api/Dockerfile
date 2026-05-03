FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
RUN npm prune --production

FROM node:20-alpine AS dev
WORKDIR /app
COPY package*.json ./
RUN npm ci
# src/ and prisma/ are mounted at runtime via volume in docker-compose.dev.yml

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
RUN apk add --no-cache vips-dev fftw-dev gcc g++ make python3 openssl openssl-dev
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/prisma ./prisma
RUN mkdir -p /app/storage
EXPOSE 3000
CMD ["sh", "-c", "npx prisma migrate deploy && node dist/main"]
