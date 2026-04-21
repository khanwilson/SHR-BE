export const configuration = () => ({
  port: parseInt(process.env.PORT ?? '3000', 10),
  nodeEnv: process.env.NODE_ENV ?? 'development',
  apiKey: process.env.API_KEY ?? '',
  database: {
    url: process.env.DATABASE_URL ?? '',
  },
  redis: {
    url: process.env.REDIS_URL ?? 'redis://localhost:6379',
  },
  visionService: {
    url: process.env.VISION_SERVICE_URL ?? 'http://localhost:8001',
  },
  ocr: {
    provider: (process.env.OCR_PROVIDER ?? 'google_vision') as 'google_vision' | 'tesseract',
    googleCredentials: process.env.GOOGLE_APPLICATION_CREDENTIALS ?? '',
  },
  storage: {
    path: process.env.STORAGE_PATH ?? './storage',
    baseUrl: process.env.STORAGE_BASE_URL ?? 'http://localhost:3000/storage',
  },
});

export type AppConfig = ReturnType<typeof configuration>;
