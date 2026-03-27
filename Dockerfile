FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# System dependencies:
# - libreoffice: PPTX -> PDF
# - poppler-utils: required by pdf2image
# - nodejs/npm: Node worker for PPTX merge
# - fonts: reduce rendering issues in previews
# - build-essential: optional, useful if any wheel needs compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice \
    libreoffice-impress \
    poppler-utils \
    nodejs \
    npm \
    fonts-dejavu \
    fonts-liberation \
    build-essential \
    ca-certificates \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependency file first for better layer caching
COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy Node worker dependency manifest first for better layer caching
COPY workers/node_merge/package*.json ./workers/node_merge/

RUN if [ -f workers/node_merge/package.json ]; then \
      cd workers/node_merge && npm install; \
    fi

# Copy application source
COPY . .

# Create runtime directories used by job isolation
RUN mkdir -p /app/tmp/jobs

# Streamlit default port
EXPOSE 8501

# Healthier default for Streamlit inside containers
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_PORT=8501

CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]