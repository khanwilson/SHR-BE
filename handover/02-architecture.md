# 02 — Architecture

## Tổng quan hệ thống

```
Client (Mobile App / HTTP)
        │  POST /scan/upload  (x-api-key header)
        ▼
  NestJS API  (:3000)
        │
        ├── ApiKeyGuard       (auth mọi route)
        ├── ScanController    → ScanService → BullMQ queue "scan"
        ├── JobsController    → JobsService → Prisma (poll status)
        └── CertificatesController → CertificatesService → Prisma (CRUD)
        │
        ├── BullMQ Worker (ScanProcessor)
        │       │
        │       ├── OcrService          (Google Vision → Tesseract fallback)
        │       ├── ParserService       (regex extract Vietnamese fields)
        │       ├── VisionService  ─────► FastAPI vision-service (:8001)
        │       ├── CertificatesService (Prisma create Certificate + ParcelDiagram)
        │       └── StorageService      (lưu ảnh gốc + diagram image)
        │
        └── ServeStatic  /storage/*  →  STORAGE_PATH directory

  FastAPI vision-service  (:8001)
        ├── POST /parcel/extract   → CV pipeline (parcel_service)
        ├── POST /ocr/extract      → Tesseract OCR
        └── GET  /health
```

## Scan pipeline (BullMQ processor)

Mỗi `Job` chạy qua 5 bước, `progress` được cập nhật theo từng bước:

| Step | Progress | Mô tả |
| --- | --- | --- |
| 1 — OCR | 20% | Đọc ảnh → Google Vision API (hoặc Tesseract). Trả raw text |
| 2 — Parse | 40% | `ParserService.parse()` extract 9 trường từ raw text bằng regex |
| 3 — Vision | 60% | Gọi vision-service `/parcel/extract` → detect polygon thửa đất |
| 4 — Persist | 80% | `CertificatesService.create()` lưu Certificate vào DB |
| 5 — Diagram | 100% | Nếu vision thành công (≥ 3 vertices) → lưu `ParcelDiagram` + ảnh diagram |

Lỗi ở bất kỳ bước nào → `Job.status = FAILED`, re-throw để BullMQ ghi nhận.
Step 3 (vision) là **non-fatal** ở mức ScanProcessor — nếu vision-service down, certificate vẫn được tạo (không có diagram).

## Vision service pipeline (Python / OpenCV)

```
POST /parcel/extract (image + ocr_text)
        │
        ├── decode_image + resize_for_processing
        ├── extract_parcel_info          (fields Section II.1)
        ├── locate_diagram_region        (crop vùng sơ đồ)
        │
        ├── extract_from_ocr_text()  ←── ưu tiên nếu có Google Vision text
        │   hoặc extract_from_coordinate_table()   (parse bảng tọa độ VN2000)
        │       → nếu ≥ 3 vertices: return {source: "coordinate_table", ...}
        │
        └── (fallback) extract_parcel_polygon()   (OpenCV contour detection)
            + extract_edge_measurements()          (đo cạnh từ ảnh)
                → return {source: "polygon_detection", ...}
```

## Database schema (Prisma)

### Certificate
Kết quả chính sau khi scan xong.

| Column | Type | Mô tả |
| --- | --- | --- |
| `id` | uuid PK | |
| `ownerName` | String? | Tên chủ sử dụng đất |
| `parcelNumber` | String? | Số thửa đất |
| `sheetNumber` | String? | Số tờ bản đồ |
| `areaM2` | Float? | Diện tích (m²) |
| `address` | String? | Địa chỉ bất động sản |
| `purpose` | String? | Mục đích sử dụng |
| `landUseForm` | String? | Hình thức sử dụng |
| `expiryYear` | String? | Thời hạn sử dụng |
| `landOrigin` | String? | Nguồn gốc sử dụng |
| `ocrRawText` | String? | Full text OCR |
| `ocrProvider` | String | `google_vision` hoặc `tesseract` |
| `ocrConfidence` | Float? | |
| `originalImagePath` | String? | Path ảnh gốc trong storage |
| `deletedAt` | DateTime? | Soft delete |

### ParcelDiagram
Kết quả sơ đồ thửa đất, `1-1` với Certificate.

| Column | Type | Mô tả |
| --- | --- | --- |
| `certificateId` | String unique FK | |
| `vertices` | Json | `[{x, y}, ...]` — normalized coords |
| `edges` | Json | `[{from, to, length_m, confidence}, ...]` |
| `confidence` | Float | Độ tin cậy extraction |
| `vertexCount` | Int | |
| `extractionSource` | String | `coordinate_table` hoặc `polygon_detection` |
| `coordinatesVn2000` | Json? | Raw VN2000 coords nếu từ bảng tọa độ |
| `diagramImagePath` | String? | Path ảnh sơ đồ đã crop |

### Job
Tracking trạng thái async processing.

| Column | Type | Mô tả |
| --- | --- | --- |
| `status` | Enum | `QUEUED → PROCESSING → COMPLETED / FAILED` |
| `progress` | Int | 0–100 |
| `error` | String? | Thông báo lỗi nếu FAILED |
| `uploadedImagePath` | String? | Path ảnh đã upload |
| `certificateId` | String? unique FK | Set khi COMPLETED |

## Module map (api/src)

```
api/src/
├── app.module.ts           Root module — wire tất cả
├── main.ts                 Bootstrap, port, global pipes/filters
├── common/
│   ├── config/configuration.ts   Typed config từ env vars
│   ├── filters/http-exception.filter.ts
│   ├── guards/api-key.guard.ts
│   └── interceptors/transform.interceptor.ts
├── prisma/                 PrismaService (global)
├── storage/                StorageService (lưu ảnh, serve static)
├── ocr/
│   ├── ocr.service.ts      Orchestrate provider selection + fallback
│   └── providers/
│       ├── google-vision.provider.ts
│       └── tesseract.provider.ts
├── parser/                 ParserService — regex extract Vietnamese text
├── vision/                 VisionService — HTTP client gọi vision-service
├── scan/                   ScanController + ScanService (upload entrypoint)
├── queue/
│   ├── producers/scan.producer.ts   Enqueue job vào BullMQ
│   └── processors/scan.processor.ts  Worker xử lý pipeline
├── jobs/                   JobsController + JobsService (status polling)
├── certificates/           CertificatesController + CertificatesService (CRUD)
└── health/                 GET /health — liveness check
```

## Storage layout

```
STORAGE_PATH/
└── certificates/
    └── {uploadId}/
        ├── original.jpg    ảnh gốc (resized max 3000px, JPEG 90%)
        └── diagram.jpg     ảnh sơ đồ thửa đất đã crop (nếu có)
```

Served tĩnh qua `/storage/certificates/{uploadId}/original.jpg`.
