# 04 — Features & API Reference

## 4.1 Scan — Upload & xử lý ảnh

**Endpoint:** `POST /scan/upload`
**Auth:** `x-api-key` header
**Body:** `multipart/form-data`, field `image` (JPEG hoặc PNG, tối đa 20MB)

**Response:**
```json
{
  "jobId": "uuid",
  "status": "queued",
  "estimatedSeconds": 8
}
```

Flow sau khi upload:
1. Ảnh được resize (max 3000px) và lưu vào `storage/certificates/{uploadId}/original.jpg`
2. Record `Job` được tạo với `status = QUEUED`
3. Job được đẩy vào BullMQ queue `scan`
4. Response trả về ngay — client poll `GET /jobs/:id` để biết kết quả

## 4.2 Jobs — Poll trạng thái

**Endpoint:** `GET /jobs/:id`
**Auth:** `x-api-key` header

**Response khi đang xử lý:**
```json
{
  "jobId": "uuid",
  "status": "PROCESSING",
  "progress": 40
}
```

**Response khi hoàn thành:**
```json
{
  "jobId": "uuid",
  "status": "COMPLETED",
  "progress": 100,
  "certificateId": "uuid",
  "result": {
    "certificate": {
      "id": "uuid",
      "ownerName": "Nguyễn Văn A",
      "parcelNumber": "123",
      "sheetNumber": "45",
      "areaM2": 466.5,
      "address": "Xã Bình Mỹ, Huyện Củ Chi, TP.HCM",
      "purpose": "Đất ở tại nông thôn",
      "landUseForm": "Riêng",
      "expiryYear": "Lâu dài",
      "landOrigin": "Nhà nước công nhận quyền sử dụng đất",
      "ocrProvider": "google_vision",
      "parcelDiagram": {
        "vertices": [{"x": 0.1, "y": 0.2}, ...],
        "edges": [{"from": 0, "to": 1, "length_m": 12.5, "confidence": 0.9}],
        "confidence": 0.85,
        "vertexCount": 5,
        "extractionSource": "coordinate_table"
      }
    }
  }
}
```

**Response khi thất bại:**
```json
{
  "jobId": "uuid",
  "status": "FAILED",
  "error": "OCR failed: ..."
}
```

`JobStatus` enum: `QUEUED → PROCESSING → COMPLETED | FAILED`

## 4.3 Certificates — Quản lý kết quả

### List

**Endpoint:** `GET /certificates`
**Query params:**
- `page` (default: 1)
- `limit` (default: 20, max: 100)
- `search` — tìm kiếm theo `ownerName`, `parcelNumber`, hoặc `address` (case-insensitive)

**Response:**
```json
{
  "items": [...],
  "total": 42,
  "page": 1,
  "limit": 20
}
```

### Get by ID

**Endpoint:** `GET /certificates/:id`
— Include `parcelDiagram` nếu có.

### Update

**Endpoint:** `PATCH /certificates/:id`
**Body (JSON):** bất kỳ subset của các trường:
`ownerName`, `parcelNumber`, `sheetNumber`, `areaM2`, `address`, `purpose`, `landUseForm`, `expiryYear`, `landOrigin`

Dùng để sửa khi OCR parse sai.

### Soft delete

**Endpoint:** `DELETE /certificates/:id`
— Set `deletedAt`, không xoá khỏi DB. Các query đều filter `deletedAt: null`.

## 4.4 OCR Service

File: `api/src/ocr/ocr.service.ts`

Logic chọn provider:
1. Nếu `OCR_PROVIDER=google_vision` VÀ `GOOGLE_API_KEY` có giá trị → thử Google Vision
2. Google Vision thất bại → log warning, fallback sang Tesseract
3. Nếu `OCR_PROVIDER=tesseract` hoặc Google Vision không available → dùng Tesseract

**Google Vision provider** (`google-vision.provider.ts`): Dùng `@google-cloud/vision` với API key, gọi `textDetection`. Trả full text đã ghép từ `fullTextAnnotation`.

**Tesseract provider** (`tesseract.provider.ts`): Gọi vision-service `/ocr/extract` (Python Pytesseract chạy trong container). Vision-service cần image bytes qua multipart.

## 4.5 Parser Service

File: `api/src/parser/parser.service.ts`

Nhận raw OCR text → extract 9 trường bằng regex. Mỗi trường có private method riêng:

| Method | Trường | Xử lý đặc biệt |
| --- | --- | --- |
| `extractOwnerName` | `ownerName` | Nhiều pattern: "Người sử dụng đất", "Ông/Bà", "Ông:", "Bà:" |
| `extractParcelNumber` | `parcelNumber` | "Thửa đất số:", nhiều biến thể OCR của "ư" |
| `extractSheetNumber` | `sheetNumber` | "Tờ bản đồ số:" |
| `extractArea` | `areaM2` | Priority: có "bằng chữ" → label "diện tích:" → fallback. Hỗ trợ cả `466,5` và `466.5` |
| `extractAddress` | `address` | Same-line → next-line → detect "Phường/Xã... Huyện... Tỉnh" |
| `extractPurpose` | `purpose` | "Mục đích sử dụng:" hoặc "Loại đất:" |
| `extractLandUseForm` | `landUseForm` | "Hình thức sử dụng:" — OCR thường bỏ "th" |
| `extractExpiry` | `expiryYear` | "Thời hạn sử dụng:" |
| `extractLandOrigin` | `landOrigin` | "Nguồn gốc sử dụng:" |

Regex được viết để chịu được nhiễu OCR (dấu tiếng Việt sai, ký tự thay thế).

## 4.6 Vision Service (FastAPI)

Service độc lập tại `vision-service/`, port 8001.

### Endpoints

| Method | Path | Mô tả |
| --- | --- | --- |
| `GET` | `/health` | Liveness check |
| `POST` | `/parcel/extract` | Trích xuất sơ đồ thửa đất từ ảnh |
| `POST` | `/ocr/extract` | OCR bằng Tesseract (dùng bởi Tesseract provider) |

### `/parcel/extract` pipeline

Input: `image` (multipart) + `ocr_text` (form field, optional)

1. **decode + resize** — `image_utils.py`
2. **extract_parcel_info** — extract thông tin Section II.1 từ ảnh (bổ sung cho OCR text)
3. **locate_diagram_region** — crop vùng chứa sơ đồ thửa đất
4. **Ưu tiên coordinate table:**
   - `extract_from_ocr_text(ocr_text)` — parse bảng `BẢNG LIỆT KÊ TỌA ĐỘ GÓC RANH` từ Google Vision text (chất lượng cao hơn)
   - Fallback: `extract_from_coordinate_table(diagram)` — OCR lại vùng diagram để tìm bảng
5. **Fallback polygon detection:**
   - `deskew_region` + `extract_parcel_polygon` — OpenCV contour detection
   - `extract_edge_measurements` — đo độ dài cạnh từ text trên ảnh

Response khi thành công: `success=True`, `vertices`, `edges`, `confidence`, `source`, `diagram_image_b64` (base64 ảnh diagram đã crop).

## 4.7 Health Check

**Endpoint:** `GET /health`
— Không cần auth. Dùng cho Docker health check và monitoring.
