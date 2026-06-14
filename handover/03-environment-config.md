# 03 — Environment & Config

## File `.env` (root của monorepo)

`api/src/common/config/configuration.ts` load từ `../.env` (relative so với thư mục `api`), tức là `.env` ở root monorepo.

```env
# Database
POSTGRES_PASSWORD=your_password
DATABASE_URL=postgresql://shr_user:your_password@localhost:5432/shr_db

# Redis
REDIS_PASSWORD=your_redis_password
REDIS_URL=redis://:your_redis_password@localhost:6379

# API authentication
API_KEY=your-static-api-key       # Client phải gửi trong header x-api-key

# OCR
OCR_PROVIDER=google_vision        # 'google_vision' | 'tesseract'
GOOGLE_API_KEY=AIza...            # Bắt buộc nếu OCR_PROVIDER=google_vision

# Storage
STORAGE_PATH=/app/storage         # Absolute path trong container
STORAGE_BASE_URL=https://your-domain.com/storage  # Base URL cho public URLs

# Vision service
VISION_SERVICE_URL=http://vision-service:8001   # trong Docker network
# VISION_SERVICE_URL=http://localhost:8001      # khi chạy local

# App
PORT=3000
NODE_ENV=production               # 'development' | 'production'
```

## Config keys (TypeScript)

`configuration.ts` export typed config — **dùng `ConfigService.get<T>('path')` thay vì `process.env` trực tiếp**:

| Config path | Env var | Default |
| --- | --- | --- |
| `port` | `PORT` | `3000` |
| `nodeEnv` | `NODE_ENV` | `development` |
| `apiKey` | `API_KEY` | `''` |
| `database.url` | `DATABASE_URL` | `''` |
| `redis.url` | `REDIS_URL` | `redis://localhost:6379` |
| `visionService.url` | `VISION_SERVICE_URL` | `http://localhost:8001` |
| `ocr.provider` | `OCR_PROVIDER` | `google_vision` |
| `ocr.googleApiKey` | `GOOGLE_API_KEY` | `''` |
| `storage.path` | `STORAGE_PATH` | `./storage` |
| `storage.baseUrl` | `STORAGE_BASE_URL` | `http://localhost:3000/storage` |

## OCR provider

Chọn qua `OCR_PROVIDER`:

| Provider | Điều kiện | Ghi chú |
| --- | --- | --- |
| `google_vision` | `GOOGLE_API_KEY` phải có giá trị | Chất lượng cao hơn, hỗ trợ tiếng Việt tốt |
| `tesseract` | Tesseract phải được cài trong container/máy host | Fallback khi Google Vision fail hoặc không có key |

Google Vision fail → **tự động fallback sang Tesseract** (không throw lỗi ra ngoài).
Nếu `OCR_PROVIDER=tesseract` hoặc Google Vision không available → dùng Tesseract trực tiếp.

## Authentication

Tất cả routes (`/scan`, `/jobs`, `/certificates`) đều được bảo vệ bởi `ApiKeyGuard`.

```
Header: x-api-key: <API_KEY>
```

Nếu thiếu hoặc sai key → `401 Unauthorized`.

## Docker Compose networking

Trong Docker Compose, các service giao tiếp qua service name:
- api → `http://postgres:5432`
- api → `http://redis:6379`
- api → `http://vision-service:8001`

Khi chạy api local (không Docker), đổi `VISION_SERVICE_URL=http://localhost:8001`.

## Secrets — không commit vào repo

| Biến | Dùng cho |
| --- | --- |
| `POSTGRES_PASSWORD` | PostgreSQL auth |
| `REDIS_PASSWORD` | Redis auth |
| `API_KEY` | Client authentication |
| `GOOGLE_API_KEY` | Google Cloud Vision API |

Không có file `.env.example` — tạo `.env` thủ công theo mẫu ở trên.
