# ============================================================
# Stage 1: Next.js フロントエンドビルド
# ============================================================
FROM node:20-slim AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./

# Next.js を静的エクスポート
ENV NEXT_PUBLIC_API_URL=""
RUN npm run build

# ============================================================
# Stage 2: Python バックエンド + 静的フロントエンド
# ============================================================
FROM python:3.11-slim

WORKDIR /app

# システム依存パッケージ
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential && \
    rm -rf /var/lib/apt/lists/*

# Python依存パッケージ
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir fastapi uvicorn sse-starlette

# アプリケーションコード
COPY config/ config/
COPY domain/ domain/
COPY infra/ infra/
COPY orchestration/ orchestration/
COPY backend/ backend/
COPY data/ data/
COPY image/ image/

# Next.js静的ビルドをコピー（FastAPIから配信）
COPY --from=frontend-builder /app/frontend/out /app/static

# Cloud Run用ポート
ENV PORT=8080
EXPOSE 8080

# FastAPIを起動
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080"]
