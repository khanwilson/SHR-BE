# SHR-BE — Handover

**Repository:** SHR-BE (local monorepo)

Backend hệ thống quét và trích xuất thông tin từ **Sổ Hồng** (Giấy chứng nhận quyền sử dụng đất Việt Nam). Người dùng upload ảnh sổ hồng, hệ thống OCR → parse → trả về các trường thông tin và sơ đồ thửa đất dạng polygon.

> Hai service độc lập: **api** (NestJS) xử lý nghiệp vụ và **vision-service** (FastAPI/Python) xử lý OpenCV. API gọi vision-service qua HTTP.

## Handover index

| Doc | Nội dung |
| --- | --- |
| [01-setup.md](01-setup.md) | Prerequisites, cài đặt, chạy local, lệnh dev |
| [02-architecture.md](02-architecture.md) | Data flow, module map, queue pipeline, database schema |
| [03-environment-config.md](03-environment-config.md) | Biến môi trường, OCR provider, storage, API key |
| [04-features.md](04-features.md) | Endpoints, scan pipeline chi tiết, OCR, parser, vision |
| [05-conventions.md](05-conventions.md) | Cấu trúc thư mục, pattern NestJS, quy ước code |
| [06-troubleshooting.md](06-troubleshooting.md) | Lỗi thường gặp, debug tips |

## 60-second orientation

- **Entry point (api):** `api/src/main.ts` → `AppModule`. Mọi request đều qua `ApiKeyGuard` (header `x-api-key`).
- **Upload flow:** `POST /scan/upload` → `ScanService.initiateProcessing()` → lưu file → tạo `Job` → đẩy vào BullMQ queue `scan` → trả về `{ jobId, status: 'queued' }`.
- **Queue processor:** `ScanProcessor` chạy 5 bước tuần tự: OCR → parse → vision → tạo `Certificate` → lưu `ParcelDiagram`.
- **Poll kết quả:** `GET /jobs/:id` — khi `status === 'COMPLETED'` thì có `result.certificate`.
- **Quản lý certificate:** `GET/PATCH/DELETE /certificates` — soft delete, pagination, search.
- **OCR:** ưu tiên Google Vision API, fallback sang Tesseract (cài trên máy host). Cấu hình qua env `OCR_PROVIDER`.
- **Vision service:** FastAPI port 8001. Nhận ảnh → OpenCV detect polygon thửa đất hoặc parse bảng tọa độ VN2000.
- **Storage:** file ảnh lưu vào `STORAGE_PATH` (mặc định `./storage`), serve tĩnh qua `/storage/*`.

## Project facts

- **api:** NestJS **11**, TypeScript **5**, Prisma **5.22**, Node **≥ 20**
- **vision-service:** FastAPI **0.111**, Python **3.11+**, OpenCV **4.10**, Tesseract
- **Database:** PostgreSQL **16** (`shr_db`)
- **Queue:** Redis **7** + BullMQ **5**
- **Auth:** static API key via header `x-api-key`
- **3 models:** `Certificate`, `ParcelDiagram`, `Job`
- Git: branch `main`
