# Plan MVP App Sổ Hồng — Expo Only

> **Phạm vi:** MVP/Proof-of-Concept, **không có backend**. Mục tiêu: chứng minh app chạy được end-to-end, dùng cá nhân hoặc demo với vài người thân cận.  
> **Stack:** Expo + React Native + TypeScript, data lưu local, OCR on-device + optional cloud (self-managed key).

---

## 1. Nguyên tắc của MVP này

1. **Nhanh trên hết** — 2,3 ngày có app chạy được.
2. **Offline-first** — data lưu trên máy user, không cần server.
3. **One-user-one-device** — không multi-device sync. Đổi máy thì làm lại.
4. **OCR on-device trước, cloud là tùy chọn** — ML Kit miễn phí, không lộ key. Nếu muốn chính xác hơn, user tự nhập API key Google Vision của họ vào Settings.
5. **Chấp nhận giới hạn của phần vẽ thửa đất** — không làm auto extraction phức tạp ở MVP này. User vẽ thủ công hoặc nhập số đo cạnh, app render lại.

---

## 2. Những gì MVP này LÀM và KHÔNG LÀM

### ✅ LÀM

- Chụp ảnh sổ hồng với auto-crop perspective
- OCR text on-device để trích xuất: tên chủ, số thửa, số tờ, diện tích, địa chỉ
- Cho phép user chỉnh sửa mọi field OCR được
- **Flow nhập thửa đất bán tự động**: user nhập số đo các cạnh + góc (hoặc chọn hình dạng preset) → app tự vẽ polygon
- Render SVG thửa đất với đầy đủ label cạnh, zoom/pan
- Lưu danh sách sổ vào máy, có search
- Export thông tin sổ ra text/JSON để share

### ❌ KHÔNG LÀM

- Backend, server, database online
- Auth, đăng ký, đăng nhập
- Sync multi-device
- Tự động detect polygon từ hình vẽ trong sổ (quá phức tạp khi không có OpenCV/BE)
- Share giữa user với nhau
- Tích hợp bản đồ thật
- Cloud storage ảnh

---

## 3. Kiến trúc tổng thể

```
┌─────────────────────────────────────────────────────────┐
│  EXPO APP (tất cả chạy trên device)                     │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Camera +     │→ │ ML Kit OCR   │→ │ Form sửa     │  │
│  │ Doc Scanner  │  │ (on-device)  │  │ field text   │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                             │           │
│                                             ▼           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Parcel       │← │ Nhập số đo   │← │ Chọn hình    │  │
│  │ SVG render   │  │ các cạnh     │  │ dạng preset  │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                             │           │
│                                             ▼           │
│  ┌─────────────────────────────────────────────────┐   │
│  │ SQLite (expo-sqlite) + FileSystem               │   │
│  │ Lưu sổ + ảnh gốc trong app documents            │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  (Tùy chọn nâng cao:)                                   │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Settings → User tự nhập Google Vision API key   │   │
│  │ → Dùng cloud OCR cho độ chính xác cao hơn       │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

**Không có network request nào bắt buộc.** App chạy offline 100%. Chỉ khi user tự bật cloud OCR thì mới gọi ra ngoài.

---

## 4. Stack công nghệ

### 4.1 Core

| Mục đích   | Thư viện                                    | Ghi chú                                          |
| ---------- | ------------------------------------------- | ------------------------------------------------ |
| Framework  | **Expo SDK (latest)** + **Expo Dev Client** | Bắt buộc Dev Client vì dùng ML Kit native module |
| Ngôn ngữ   | **TypeScript**                              | Type safety                                      |
| Navigation | **Expo Router**                             | File-based, type-safe                            |

### 4.2 Quét ảnh + OCR

| Mục đích                           | Thư viện                                                             |
| ---------------------------------- | -------------------------------------------------------------------- |
| Camera                             | `expo-camera`                                                        |
| Document scanner (auto crop 4 góc) | `react-native-document-scanner-plugin`                               |
| Image picker (từ thư viện)         | `expo-image-picker`                                                  |
| Image manipulation                 | `expo-image-manipulator`                                             |
| OCR on-device                      | `@react-native-ml-kit/text-recognition`                              |
| OCR cloud (tùy chọn)               | Gọi trực tiếp Google Vision API qua `fetch` với key user tự cấu hình |

### 4.3 Vẽ thửa đất

| Mục đích                               | Thư viện                                                   |
| -------------------------------------- | ---------------------------------------------------------- |
| SVG render                             | `react-native-svg`                                         |
| Gesture (pinch zoom, pan, drag vertex) | `react-native-gesture-handler` + `react-native-reanimated` |
| Hình học (tính polygon từ cạnh + góc)  | Tự viết `parcel-geometry.ts` với logic tam giác lượng      |

### 4.4 Data + state

| Mục đích                        | Thư viện                                                          |
| ------------------------------- | ----------------------------------------------------------------- |
| Local DB                        | `expo-sqlite` (có API mới rất gọn)                                |
| ORM nhẹ (tùy chọn)              | `drizzle-orm` với adapter expo-sqlite                             |
| Lưu file ảnh                    | `expo-file-system`                                                |
| Settings (API key, preferences) | `expo-secure-store` (cho key) + `expo-mmkv` (cho settings thường) |
| Global state                    | `zustand`                                                         |
| Form                            | `react-hook-form` + `zod`                                         |

### 4.5 UI / UX

| Mục đích          | Thư viện                                     |
| ----------------- | -------------------------------------------- |
| Component library | `react-native-paper` hoặc `tamagui` — chọn 1 |
| Icon              | `@expo/vector-icons` (có sẵn)                |
| Toast             | `react-native-toast-message`                 |
| Bottom sheet      | `@gorhom/bottom-sheet`                       |

### 4.6 Dev tools

| Mục đích        | Thư viện                             |
| --------------- | ------------------------------------ |
| Package manager | `pnpm` hoặc `bun`                    |
| Linting         | ESLint + Prettier (theo preset Expo) |
| Error tracking  | `sentry-expo` (free tier)            |
| Build           | **EAS Build** (free tier đủ MVP)     |

---

## 5. Cấu trúc thư mục

```
so-hong-mvp/
├── app/                          # Expo Router screens
│   ├── _layout.tsx
│   ├── index.tsx                 # Home — danh sách sổ
│   ├── scan/
│   │   ├── camera.tsx            # Bước 1: chụp ảnh
│   │   ├── review.tsx            # Bước 2: xem OCR, sửa text
│   │   ├── parcel.tsx            # Bước 3: nhập thửa đất
│   │   └── done.tsx              # Bước 4: preview + save
│   ├── book/
│   │   └── [id].tsx              # Chi tiết 1 sổ
│   └── settings/
│       ├── index.tsx
│       └── ocr-config.tsx        # Config cloud OCR (tùy chọn)
│
├── src/
│   ├── components/
│   │   ├── ParcelSvg.tsx         # Render polygon thửa đất
│   │   ├── ParcelEditor.tsx      # UI nhập cạnh + góc
│   │   ├── EditableField.tsx
│   │   ├── BookCard.tsx
│   │   └── ShapePresets.tsx      # Chọn hình chữ nhật/tam giác/ngũ giác...
│   │
│   ├── services/
│   │   ├── ocr/
│   │   │   ├── ml-kit.service.ts       # OCR on-device
│   │   │   ├── google-vision.service.ts # OCR cloud (optional)
│   │   │   └── index.ts                # Chọn provider theo settings
│   │   ├── parser/
│   │   │   └── so-hong.parser.ts       # Regex trích xuất fields VN
│   │   ├── geometry/
│   │   │   └── parcel.geometry.ts      # Tính polygon từ cạnh + góc
│   │   ├── db/
│   │   │   ├── schema.ts               # Drizzle schema
│   │   │   └── client.ts
│   │   └── storage/
│   │       └── images.ts               # Lưu ảnh vào FileSystem
│   │
│   ├── stores/
│   │   ├── scan.store.ts         # State tạm của flow scan hiện tại
│   │   └── settings.store.ts
│   │
│   ├── hooks/
│   │   ├── useCamera.ts
│   │   ├── useOcr.ts
│   │   └── useParcelGeometry.ts
│   │
│   ├── types/
│   │   └── index.ts              # SoHong, Parcel, Vertex, Edge...
│   │
│   └── utils/
│       ├── date.ts
│       ├── format.ts
│       └── validators.ts
│
├── assets/
├── app.json
├── package.json
└── tsconfig.json
```

---

## 6. Flow chi tiết

### Flow A: Quét sổ mới

```
[Home] → bấm "+ Quét sổ mới"
   ↓
[Camera screen]
   - expo-camera mở với overlay khung
   - User chụp
   - react-native-document-scanner-plugin auto crop 4 góc
   - Preview, bấm "Dùng ảnh này" hoặc "Chụp lại"
   ↓
[Review screen — OCR text]
   - Hiển thị ảnh đã crop bên trên
   - Chạy ML Kit OCR (1-2 giây)
   - Parser regex trích các field: tên chủ, số thửa, số tờ, diện tích, địa chỉ, mục đích, thời hạn
   - Form với mỗi field là 1 input có thể chỉnh sửa
   - Nút "Tiếp tục"
   ↓
[Parcel screen — nhập thửa đất]
   - Lựa chọn:
     A) Chọn hình dạng preset (chữ nhật/vuông/tam giác/ngũ giác đều...)
     B) Nhập số đo N cạnh + N góc
     C) (Tùy chọn nâng cao sau) Vẽ tay trên canvas
   - Sau khi có dữ liệu → geometry service tính toán vertices
   - Preview SVG sống realtime khi user nhập
   - Nút "Hoàn tất"
   ↓
[Done screen]
   - Preview full: ảnh gốc + form text + SVG thửa đất
   - Nút "Lưu vào máy"
   ↓
[Home] với sổ mới trong danh sách
```

### Flow B: Xem lại sổ đã lưu

```
[Home] → bấm 1 item trong list
   ↓
[Book detail screen]
   - Tab "Thông tin": các field text
   - Tab "Thửa đất": SVG render với pinch zoom
   - Tab "Ảnh gốc": ảnh sổ hồng đã chụp
   - Nút "Sửa", "Xóa", "Chia sẻ" (export JSON/text)
```

---

## 7. Phần "nhập thửa đất bán tự động" — giải pháp thay thế OpenCV

Vì không có backend + OpenCV, ta thiết kế UX khéo để user tự nhập nhanh mà vẫn chính xác:

### Option 1 — Preset (nhanh nhất, cho thửa đơn giản)

```
Chọn hình dạng:
[  ] Hình chữ nhật     → nhập 2 số: dài × rộng
[  ] Hình vuông        → nhập 1 số: cạnh
[  ] Hình tam giác     → nhập 3 cạnh
[  ] Hình thang         → nhập 4 cạnh + 1 góc
[  ] Đa giác tự do     → chuyển sang Option 2
```

Đa số sổ hồng cá nhân ở VN là chữ nhật → preset giải quyết được ~60% case nhanh trong vài giây.

### Option 2 — Nhập số đo cạnh và góc

User nhập dạng bảng:

```
Cạnh 1: 12.5 m    Góc sau cạnh 1: 90°
Cạnh 2: 8.3 m     Góc sau cạnh 2: 90°
Cạnh 3: 12.5 m    Góc sau cạnh 3: 90°
Cạnh 4: 8.3 m     (góc cuối tự động)
```

Thuật toán `parcel.geometry.ts`:

```typescript
function computeVertices(edges: number[], angles: number[]): Vertex[] {
  const vertices: Vertex[] = [{ x: 0, y: 0 }];
  let currentAngle = 0; // bearing hiện tại

  for (let i = 0; i < edges.length; i++) {
    const last = vertices[vertices.length - 1];
    const dx = edges[i] * Math.cos(currentAngle);
    const dy = edges[i] * Math.sin(currentAngle);
    vertices.push({ x: last.x + dx, y: last.y + dy });

    // xoay theo góc trong tại đỉnh tiếp theo
    currentAngle += Math.PI - degToRad(angles[i]);
  }

  return vertices;
}
```

Sau đó auto-fit vào viewBox của SVG để hiển thị.

### Option 3 (nâng cao, làm sau) — Vẽ tay trên ảnh

Overlay transparent canvas lên ảnh bản vẽ trong sổ, user tap lần lượt vào các đỉnh. Chỉ cần 4-6 tap là xong. Sau đó app hỏi số đo từng cạnh và user gõ vào.

Cho MVP này ưu tiên Option 1 + 2. Option 3 để sprint sau.

---

## 8. Database schema (Drizzle + SQLite)

```typescript
// src/services/db/schema.ts
import { sqliteTable, text, integer, real } from "drizzle-orm/sqlite-core";

export const soHongs = sqliteTable("so_hongs", {
  id: text("id").primaryKey(),

  // Text fields
  ownerName: text("owner_name"),
  parcelNumber: text("parcel_number"), // số thửa
  sheetNumber: text("sheet_number"), // số tờ
  area: real("area"), // m²
  address: text("address"),
  purpose: text("purpose"),
  expiryDate: text("expiry_date"), // ISO string

  // Parcel geometry (JSON stringified)
  parcelGeometry: text("parcel_geometry"),
  // { vertices: [{x, y}...], edges: [{from, to, length, angle}...] }

  // Local file paths
  originalImagePath: text("original_image_path"),

  // Metadata
  ocrProvider: text("ocr_provider"), // 'mlkit' | 'google'
  ocrRawText: text("ocr_raw_text"), // để debug

  createdAt: integer("created_at", { mode: "timestamp" }).notNull(),
  updatedAt: integer("updated_at", { mode: "timestamp" }).notNull(),
});
```

Ảnh lưu trong `FileSystem.documentDirectory + 'so-hongs/{id}/original.jpg'`. DB chỉ lưu path.

---

## 9. Roadmap 2-3 tuần

### Tuần 1 — Foundation + Scan flow

**Ngày 1-2: Setup**

- [ ] `npx create-expo-app` với template TypeScript
- [ ] Cài Expo Dev Client, build lên máy thật thử
- [ ] Setup Expo Router, layout cơ bản
- [ ] Setup expo-sqlite + Drizzle, migration đầu tiên
- [ ] Setup zustand, react-hook-form, zod

**Ngày 3-4: Camera + Document Scanner**

- [ ] Screen camera với `expo-camera`
- [ ] Tích hợp `react-native-document-scanner-plugin`
- [ ] Preview + retake UI
- [ ] Lưu ảnh vào FileSystem

**Ngày 5-7: OCR on-device**

- [ ] Tích hợp ML Kit Text Recognition
- [ ] Viết `so-hong.parser.ts` với regex cho các field VN:
  - Số thửa: `/thửa\s+đất\s+số[:\s]+(\d+)/i`
  - Số tờ: `/tờ\s+bản\s+đồ[:\s]+(\d+)/i`
  - Diện tích: `/diện\s+tích[:\s]+([\d.,]+)\s*m/i`
  - Tên chủ: tìm sau "Ông/Bà:" hoặc "Người sử dụng đất:"
- [ ] Screen Review với form sửa
- [ ] Test với 10 ảnh sổ thật để tinh chỉnh regex

### Tuần 2 — Parcel + SVG

**Ngày 8-9: Parcel geometry**

- [ ] Viết `parcel.geometry.ts` tính vertices từ cạnh + góc
- [ ] Unit test với vài hình chuẩn (vuông, chữ nhật, ngũ giác)
- [ ] Function auto-fit vào viewBox

**Ngày 10-11: ParcelSvg component**

- [ ] Render polygon với `react-native-svg`
- [ ] Label cạnh với số đo (đặt tại trung điểm mỗi cạnh)
- [ ] Label đỉnh (A, B, C, D...)
- [ ] North arrow (mũi tên chỉ hướng bắc)
- [ ] Pinch zoom + pan với gesture-handler

**Ngày 12-14: Parcel editor**

- [ ] Screen chọn hình dạng preset
- [ ] Form nhập cạnh + góc cho đa giác tự do
- [ ] Preview SVG realtime khi user đang gõ
- [ ] Validate: tổng góc trong = (n-2)×180°, polygon đóng kín

### Tuần 3 — Polish + lưu trữ + testing

**Ngày 15-16: Home + list + detail**

- [ ] Home với danh sách sổ, pull-to-refresh, search
- [ ] BookCard với thumbnail SVG mini
- [ ] Detail screen 3 tabs: info / thửa / ảnh

**Ngày 17-18: Settings + Cloud OCR optional**

- [ ] Settings screen
- [ ] Config nhập Google Vision API key (lưu expo-secure-store)
- [ ] Toggle "Dùng cloud OCR cho độ chính xác cao"
- [ ] Implement `google-vision.service.ts`

**Ngày 19-20: Polish**

- [ ] Empty states, loading states đẹp
- [ ] Error handling, toast
- [ ] Icon app, splash screen
- [ ] Sentry integration

**Ngày 21: EAS Build + test**

- [ ] EAS Build cho Android APK
- [ ] EAS Build cho iOS (nếu có tài khoản Apple Dev)
- [ ] Test với 20-30 ảnh sổ thật
- [ ] Fix bugs priority cao

---

## 10. Chi phí

| Khoản                                     | Chi phí                                 |
| ----------------------------------------- | --------------------------------------- |
| Expo EAS                                  | $0 (free tier đủ 30 builds/tháng)       |
| ML Kit OCR                                | $0 (on-device)                          |
| Google Vision (tùy chọn, user tự trả)     | $0 với free tier 1000/tháng             |
| Apple Developer Account (nếu publish iOS) | $99/năm                                 |
| Google Play Developer                     | $25 one-time                            |
| Domain/hosting                            | $0 (không cần)                          |
| **Tổng MVP**                              | **$0** cho Android, **$99/năm** nếu iOS |

---

## 11. Giới hạn cần chấp nhận và kế hoạch tiến hoá

### Giới hạn hiện tại

1. **Không sync** — đổi máy thì mất data. Workaround: cho user export JSON/backup file.
2. **OCR on-device kém hơn cloud** cho sổ cũ, giấy mờ. Workaround: cho user tự bật cloud OCR.
3. **Thửa đất phải nhập thủ công** — không auto từ bản vẽ. Workaround: preset + form nhanh.
4. **Không có account, không share** được giữa user với nhau.

### Khi nào nâng cấp lên có backend?

Khi đạt **ít nhất 1** trong các tiêu chí:

- Có >50 user thật xài đều đặn → cần sync + cloud backup
- Có feedback "tôi muốn tự động nhận diện bản vẽ" nhiều → cần OpenCV trên BE
- Muốn publish commercial trên Store → cần giấu API key, không dùng key user
- Cần tính năng chia sẻ / multi-user

Lúc đó mới theo plan NestJS đầy đủ. Plan MVP này đã thiết kế sao cho **code có thể refactor lên backend không mất công**: service layer `ocr/` và `parser/` có interface rõ ràng, chỉ cần đổi implementation thành HTTP call.

---

## 12. Rủi ro kỹ thuật và mitigation

| Rủi ro                                                                       | Mitigation                                                     |
| ---------------------------------------------------------------------------- | -------------------------------------------------------------- |
| `react-native-document-scanner-plugin` không tương thích Expo Dev Client mới | Fallback: dùng `expo-image-manipulator` + UI vẽ 4 góc thủ công |
| ML Kit OCR đọc sai nhiều với sổ hồng VN                                      | Dù sao cũng cho phép sửa tay mọi field. Thêm cloud OCR option  |
| User vẽ thửa đất sai → polygon tự giao cắt                                   | Validate polygon, cảnh báo, highlight đỏ                       |
| Ảnh sổ hồng lớn → app chậm, nóng máy                                         | Resize xuống max 2000px trước khi OCR                          |
| SQLite migration khi update app                                              | Dùng Drizzle migrations ngay từ đầu                            |

---

## 13. Quyết định thiết kế quan trọng

### Vì sao chọn ML Kit làm OCR chính thay vì cloud?

- **Miễn phí, không lộ key, chạy offline** — quan trọng nhất cho MVP không BE
- Đủ dùng cho chữ in rõ ràng (đa số sổ hồng mới)
- Độ trễ <1 giây, UX mượt
- Cloud OCR chỉ là tính năng nâng cao cho user cần độ chính xác cao

### Vì sao KHÔNG tự động trích polygon?

- Bài toán khó cần OpenCV đúng cách, trên mobile JS không stable
- MVP cần tập trung validate giá trị sản phẩm trước, không sa đà kỹ thuật
- UX nhập preset/form rất nhanh (vài giây) cho đa số thửa đơn giản
- Nếu user thấy giá trị → ta mới đầu tư xây auto extraction ở giai đoạn 2 với backend

### Vì sao dùng Drizzle thay vì raw SQL?

- Type-safe — IDE autocomplete khi query
- Migration tự động
- Overhead nhỏ, performance gần như raw
- Code sạch hơn, dễ maintain

---

## 14. Câu hỏi cần làm rõ với bản thân trước khi code

1. MVP này để **dùng cá nhân** hay **demo cho khách hàng/nhà đầu tư**? Ảnh hưởng mức độ polish.
2. Target **Android only** hay **cả iOS**? iOS tốn $99/năm và review lâu hơn.
3. **Dataset ảnh sổ hồng thật** — có bao nhiêu ảnh để test? Càng nhiều càng tốt, tối thiểu 20 ảnh đa dạng.
4. Có cần feature **import ảnh từ máy** (không chụp trực tiếp) không? Khuyến nghị có, dễ thêm và hữu ích.

---

## 15. Sau MVP này làm gì tiếp?

Sau khi MVP chạy được và có feedback, đánh giá theo thứ tự ưu tiên:

1. **Nếu user than OCR sai nhiều** → đầu tư cloud OCR mặc định (cần BE để giấu key)
2. **Nếu user muốn auto vẽ polygon** → build BE với OpenCV + Node/Nest
3. **Nếu user muốn đổi máy không mất data** → build auth + sync
4. **Nếu có nhu cầu commercial** → làm account, pricing, in-app purchase
5. **Nếu muốn tích hợp bản đồ thật** → Mapbox/Google Maps + GPS geocoding

Lúc đó quay về plan NestJS đầy đủ, code mobile hầu như không phải viết lại, chỉ thay service layer.

---

_Plan này ưu tiên tốc độ ra MVP trong 2-3 tuần với chi phí gần $0 để validate ý tưởng. Đã cố ý bỏ qua những phần phức tạp (BE, auto polygon extraction, sync) để tập trung vào core value: "chụp sổ → thấy lại thông tin + hình thửa đẹp". Nếu validate tốt, plan NestJS đầy đủ là bước tiếp theo tự nhiên._
