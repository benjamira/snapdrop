# --- Frontend bauen ---
FROM node:22-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- Laufzeit: FastAPI liefert API + gebautes Frontend (ADR 0001) ---
FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1 TZ=UTC \
    SNAPDROP_DB=/data/snapdrop.db USERS_FILE=/config/users.yaml STATIC_DIR=/app/static
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/*.py ./
COPY backend/providers ./providers
COPY --from=web /web/dist ./static
RUN mkdir /data /config && chown 1001:1001 /data
USER 1001:1001
VOLUME /data
EXPOSE 8000
HEALTHCHECK --interval=60s --timeout=5s --start-period=15s \
  CMD python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/api/health', timeout=4)"
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
