# Multi-target Dockerfile retained for compatibility.
# Prefer backend/Dockerfile and frontend/Dockerfile.

FROM python:3.12-slim AS backend
WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt
COPY backend/ /app/backend/
WORKDIR /app/backend
ENV PYTHONPATH=/app/backend
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM node:20-slim AS frontend-build
ARG PUBLIC_API_URL=http://localhost:8000
ENV PUBLIC_API_URL=$PUBLIC_API_URL
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* /app/frontend/
WORKDIR /app/frontend
RUN npm ci 2>/dev/null || npm install
COPY frontend/ /app/frontend/
RUN npm run build

FROM node:20-slim AS frontend
WORKDIR /app/frontend
COPY --from=frontend-build /app/frontend/build ./build
COPY --from=frontend-build /app/frontend/package.json ./
COPY --from=frontend-build /app/frontend/node_modules ./node_modules
EXPOSE 3000
ENV NODE_ENV=production
CMD ["node", "build"]
