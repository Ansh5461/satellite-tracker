FROM python:3.12-slim AS builder
WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir --upgrade pip \
    && pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

FROM python:3.12-slim AS runtime
WORKDIR /app
RUN useradd --create-home --uid 10001 appuser
COPY --from=builder /wheels /wheels
COPY requirements.txt ./
# Prefer the wheelhouse; allow PyPI only if a wheel is missing.
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels
COPY app ./app
COPY data ./data
COPY scripts ./scripts
USER appuser
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
