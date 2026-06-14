# 01 — Setup & Run

## Prerequisites

| Tool | Version / ghi chú |
| --- | --- |
| **Node** | 20.x+ |
| **npm** | đi kèm Node (không dùng yarn/pnpm) |
| **Docker + Docker Compose** | bất kỳ bản ổn định gần đây |
| **Python** | 3.11+ (chỉ nếu chạy vision-service local không qua Docker) |
| **Tesseract OCR** | cài trên máy host nếu dùng `OCR_PROVIDER=tesseract` local |

Chạy production / staging → dùng Docker Compose, không cần cài Python/Tesseract trên host.

## Cài đặt & chạy (Docker — khuyến nghị)

### 1. Tạo file `.env` ở root

```sh
cp .env.example .env  # nếu có, hoặc tạo mới theo 03-environment-config.md
```

Các biến bắt buộc:

```env
POSTGRES_PASSWORD=secret
REDIS_PASSWORD=secret
API_KEY=your-api-key
GOOGLE_API_KEY=your-google-vision-api-key   # nếu dùng Google Vision
STORAGE_BASE_URL=http://localhost:3000/storage
```

### 2. Chạy production stack

```sh
docker compose up --build
```

Services sẽ khởi động theo thứ tự: postgres → redis → vision-service → api.
Health check đảm bảo api chỉ start sau khi postgres, redis, và vision-service healthy.

### 3. Chạy development (hot-reload)

```sh
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

- **api** mount `./api/src` và `./api/prisma` vào container, chạy `nest start --watch`.
- **vision-service** mount `./vision-service/app`, chạy uvicorn `--reload`.

## Cài đặt database (lần đầu hoặc sau khi thêm migration)

```sh
# Chạy trong container api đang chạy:
docker compose exec api npx prisma migrate deploy

# Hoặc local (cần DATABASE_URL trong env):
cd api && npx prisma migrate dev
```

## Chạy api local (không Docker)

```sh
cd api
npm install
npx prisma generate
npm run start:dev
```

Đảm bảo postgres và redis đang chạy (có thể dùng `docker compose up postgres redis vision-service`).

## Chạy vision-service local (không Docker)

```sh
cd vision-service
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

## Quality commands

```sh
# api
cd api
npm run lint          # ESLint
npm run test          # Jest (unit tests)
npm run test:cov      # Jest + coverage
npm run test:e2e      # E2E tests (cần DB)
npm run build         # compile TypeScript

# vision-service (nếu có test)
cd vision-service
python -m pytest tests/
```

## Ports

| Service | Port |
| --- | --- |
| api (NestJS) | 3000 |
| vision-service (FastAPI) | 8001 |
| PostgreSQL | 5432 |
| Redis | 6379 |
