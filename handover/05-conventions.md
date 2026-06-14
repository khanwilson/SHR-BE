# 05 — Conventions & Cấu trúc code

## Monorepo layout

```
SHR-BE/
├── api/                    NestJS backend (TypeScript)
│   ├── src/
│   │   ├── common/         Guards, filters, interceptors, config — shared infrastructure
│   │   ├── prisma/         PrismaService (global module)
│   │   ├── storage/        StorageService — lưu/đọc file
│   │   ├── ocr/            OcrService + providers
│   │   ├── parser/         ParserService — regex Vietnamese text
│   │   ├── vision/         VisionService — HTTP client gọi vision-service
│   │   ├── scan/           Upload entrypoint
│   │   ├── queue/          BullMQ producer + processor
│   │   ├── jobs/           Job status tracking
│   │   ├── certificates/   Certificate CRUD
│   │   └── health/         Health check
│   ├── prisma/
│   │   └── schema.prisma
│   └── package.json
├── vision-service/         FastAPI service (Python)
│   ├── app/
│   │   ├── cv/             OpenCV modules (mỗi file = một concern)
│   │   ├── routers/        FastAPI route handlers
│   │   ├── services/       Business logic (parcel_service, ocr_service)
│   │   ├── schemas/        Pydantic schemas
│   │   └── main.py
│   └── requirements.txt
├── docker-compose.yml
├── docker-compose.dev.yml
└── .env                    (gitignored)
```

## NestJS patterns

### Module structure
Mỗi feature có 1 module riêng: `feature.module.ts`, `feature.controller.ts`, `feature.service.ts`.
Module phải được import trong `AppModule`.

### Dependency injection
Dùng constructor injection. Không new service trực tiếp.

```ts
@Injectable()
export class MyService {
  constructor(
    private prisma: PrismaService,
    private config: ConfigService,
  ) {}
}
```

### Config — không dùng process.env trực tiếp
Luôn dùng `ConfigService.get<string>('path.to.key')` với typed config từ `configuration.ts`.

### Guards
Tất cả controller phải có `@UseGuards(ApiKeyGuard)` ở class level (không phải method level).
Ngoại lệ: `HealthController` không cần guard.

### Error handling
- Throw `NotFoundException`, `BadRequestException` từ `@nestjs/common` — `HttpExceptionFilter` sẽ format response.
- Trong processor, re-throw lỗi để BullMQ ghi nhận job failed.
- Không swallow lỗi bằng try/catch trống.

### Validation
Dùng `class-validator` + `class-transformer` với `ValidationPipe` global. DTO có decorator `@IsString()`, `@IsOptional()`, v.v.

## Prisma conventions

- Tất cả model có `id` (uuid), `createdAt`, `updatedAt`.
- Soft delete: thêm `deletedAt DateTime?`, query luôn filter `{ deletedAt: null }`.
- Không raw SQL — dùng Prisma client API.
- Sau khi sửa `schema.prisma`: `npx prisma migrate dev --name <tên>`.
- Trong CI/production: `npx prisma migrate deploy` (không tạo migration mới).

## BullMQ conventions

- Queue name: `SCAN_QUEUE = 'scan'` — định nghĩa trong `queue.constants.ts`.
- Producer (`scan.producer.ts`): inject `@InjectQueue(SCAN_QUEUE)`, method `enqueue()`.
- Processor (`scan.processor.ts`): `@Processor(SCAN_QUEUE)`, extends `WorkerHost`, override `process()`.
- Job data type: `ScanJobData = { jobId: string; imagePath: string }`.

## Python / FastAPI conventions

- Mỗi CV concern = 1 file trong `app/cv/` (không đặt logic xử lý ảnh trong router).
- Route handlers trong `app/routers/` chỉ validate input + gọi service, không chứa business logic.
- Blocking OpenCV code chạy trong `ThreadPoolExecutor` qua `loop.run_in_executor()` — không block event loop.
- Exception trong pipeline: catch tất cả, trả `{"success": False, "error": str(exc)}` — không để 500 propagate.

## Naming

- **NestJS services:** `PascalCase`, suffix `Service` / `Controller` / `Module` / `Guard`
- **Files:** `kebab-case.ts` (NestJS convention)
- **Python:** `snake_case` cho functions và files
- **Env vars:** `SCREAMING_SNAKE_CASE`
- **Database columns:** `camelCase` trong Prisma schema → PostgreSQL auto-maps sang `snake_case`

## Không làm

- Không commit `.env` hoặc credentials vào git
- Không dùng `process.env` trực tiếp trong service code
- Không tạo Axios instance thứ hai trong api — dùng `HttpService` từ `@nestjs/axios`
- Không bỏ `@UseGuards(ApiKeyGuard)` ở bất kỳ controller mới nào (trừ health)
- Không xoá cứng certificate khỏi DB — dùng soft delete
