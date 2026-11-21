FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai

WORKDIR /app

# 依赖层单独缓存
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt psycopg[binary]

COPY app ./app
COPY scripts ./scripts 2>/dev/null || true

RUN mkdir -p /app/storage /app/data

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
