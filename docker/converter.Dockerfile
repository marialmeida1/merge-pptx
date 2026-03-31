FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /srv/converter

RUN printf 'Acquire::Retries "3";\nAcquire::ForceIPv4 "true";\n' > /etc/apt/apt.conf.d/99network && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    libreoffice-core \
    libreoffice-impress \
    fonts-dejavu \
    fonts-liberation \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-converter.txt .

RUN pip install --upgrade pip && \
    pip install -r requirements-converter.txt

COPY service_apps ./service_apps

RUN mkdir -p /data/jobs && \
    useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /srv/converter /data/jobs

ENV JOB_STORAGE_ROOT=/data/jobs

USER appuser

EXPOSE 8000

CMD ["uvicorn", "service_apps.converter_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
