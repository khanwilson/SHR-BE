# 06 — Troubleshooting

## api không start được

**Lỗi: `Can't reach database server`**
- Postgres chưa ready. Chờ health check pass: `docker compose ps` → cột `Health` phải là `healthy`.
- Kiểm tra `DATABASE_URL` trong `.env` có đúng password không.

**Lỗi: `ECONNREFUSED redis`**
- Redis chưa ready hoặc sai password. Kiểm tra `REDIS_URL`.

**Lỗi: `Cannot find module '...'`**
- Quên chạy `npm install` hoặc `npx prisma generate` sau khi pull code mới.

## vision-service không respond

**api log: `Vision service failed: connect ECONNREFUSED`**
- vision-service chưa start hoặc health check chưa pass.
- Chạy local: đảm bảo `uvicorn` đang chạy ở port 8001.
- Docker: `docker compose logs vision-service` để xem lỗi import.

**vision-service log: `ModuleNotFoundError: No module named 'cv2'`**
- OpenCV chưa được cài. Trong Docker: rebuild image `docker compose build vision-service`.
- Local: `pip install opencv-python-headless==4.10.0.84`

**Lưu ý:** VisionService có `withRetry` nhưng hiện config `attempts=1` cho dev. Nếu vision-service down, job vẫn COMPLETED nhưng không có `parcelDiagram`.

## OCR cho kết quả tệ

**Tesseract không nhận ra tiếng Việt**
- Cần cài language pack `vie`. Trong Dockerfile vision-service kiểm tra `tesseract-ocr-vie` đã được cài chưa.
- Kiểm tra: `docker compose exec vision-service tesseract --list-langs`

**Google Vision trả về text rỗng**
- `GOOGLE_API_KEY` không hợp lệ hoặc API chưa được enable trên Google Cloud Console.
- Kiểm tra log: `Google Vision failed, falling back to Tesseract: ...`

**Parser trả về `null` cho nhiều trường**
- Ảnh chất lượng thấp / OCR nhận sai dấu tiếng Việt nghiêm trọng.
- Dùng `GET /jobs/:id` → `result.certificate.ocrRawText` để xem raw text, đối chiếu với ảnh gốc.
- Parser regex chịu được nhiều biến thể OCR nhưng không thể cover hết — có thể cần thêm pattern.

## Job bị stuck ở PROCESSING

Xảy ra khi api restart trong khi job đang chạy. `JobsService.resetStalledJobs()` được gọi lúc bootstrap để mark các job `PROCESSING` thành `FAILED`.

Nếu vẫn còn job stuck: chạy thủ công qua Prisma Studio hoặc SQL:
```sql
UPDATE jobs SET status = 'FAILED', error = 'Manual reset' WHERE status = 'PROCESSING';
```

## Upload lỗi 400

- `Only JPEG/PNG images are accepted` — file không phải JPEG/PNG (kiểm tra `Content-Type`).
- `Image file is required` — multipart field phải tên là `image`.
- File quá 20MB — giảm kích thước ảnh trước khi upload.

## Lỗi 401 Unauthorized

Header `x-api-key` thiếu hoặc sai. So sánh với giá trị `API_KEY` trong `.env`.
Nếu `API_KEY` là empty string trong env → mọi request đều bị reject (guard throw khi `!expected`).

## Prisma migration conflict

Khi pull code mới có migration mới:
```sh
docker compose exec api npx prisma migrate deploy
```

Nếu migration history bị diverge (dev tạo migration chưa push):
```sh
npx prisma migrate resolve --applied <migration_name>  # đánh dấu đã apply thủ công
```

## Storage file không tìm thấy

- Kiểm tra volume `app_storage` còn mount đúng không: `docker compose exec api ls /app/storage`.
- `STORAGE_BASE_URL` phải trỏ đúng domain public để URL trong response có thể access được.
- Dev local: `STORAGE_BASE_URL=http://localhost:3000/storage`.

## Prisma Studio (debug DB)

```sh
cd api && npx prisma studio
# hoặc trong container:
docker compose exec api npx prisma studio --port 5555
```

## BullMQ UI (debug queue)

Hiện tại không có Bull Board được cài sẵn. Để debug queue:
```sh
docker compose exec redis redis-cli --pass $REDIS_PASSWORD
> KEYS bull:*       # list tất cả queue keys
> LLEN bull:scan:wait   # số job đang chờ
```
