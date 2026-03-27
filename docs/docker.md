## 1. Overview

This project runs a **PPTX composition pipeline** inside a single Docker container.

The container includes:

* Python + Streamlit → application and UI
* LibreOffice → PPTX → PDF conversion
* Poppler → PDF → images
* Node.js + pptx-automizer → PPTX merge/composition

The goal is to provide a **reproducible environment** with minimal local setup.

---

## 2. Prerequisites

Ensure the following is installed on your machine:

* Docker (Docker Desktop on macOS)
* Docker daemon running

Verify:

```bash
docker version
```

---

## 3. Project Structure

```text
project/
├─ app.py
├─ requirements.txt
├─ services/
├─ workers/
│  └─ node_merge/
│     ├─ package.json
│     └─ merge_worker.js
├─ tmp/
├─ Dockerfile
└─ docker-compose.yml
```

---

## 4. Build and Run

### 4.1 Build the container

```bash
docker compose build
```

---

### 4.2 Run the application

```bash
docker compose up
```

---

### 4.3 Run in background

```bash
docker compose up -d
```

---

## 5. Access the Application

Once running, open:

```text
http://localhost:8501
```

This will load the Streamlit interface.

---

## 6. Volumes and Persistence

The following volume is mounted:

```text
./tmp → /app/tmp
```

This directory stores:

```text
tmp/jobs/
├─ inputs/
├─ previews/
├─ outputs/
├─ selection.json
├─ merge_request.json
└─ merge_result.json
```

### Purpose

* Persist uploaded files
* Store preview artifacts
* Store final outputs
* Enable debugging outside the container

---

## 7. Stopping the Application

```bash
docker compose down
```

---

## 8. Logs

To inspect logs:

```bash
docker compose logs -f
```

---

## 9. Accessing the Container

To open a shell inside the container:

```bash
docker exec -it pptx-composer bash
```

You can then validate installed tools:

```bash
soffice --version
node -v
npm -v
python --version
```

---

## 10. Rebuilding After Changes

If you modify:

* `Dockerfile`
* `requirements.txt`
* `package.json`

Rebuild the container:

```bash
docker compose up --build
```

---

## 11. Troubleshooting

### Docker daemon not running

```text
Cannot connect to the Docker daemon
```

Solution:

```bash
open -a Docker
```

Wait until Docker Desktop is fully initialized.

---

### Port already in use

If port `8501` is occupied:

Edit `docker-compose.yml`:

```yaml
ports:
  - "8502:8501"
```

Then access:

```text
http://localhost:8502
```

---

### Permission issues on `tmp/`

```bash
chmod -R 777 tmp
```

---

### LibreOffice not found (inside container)

Verify:

```bash
soffice --version
```

If missing, rebuild the image.

---

## 12. Development Workflow

Typical flow:

```text
1. Start container
2. Upload PPTX files
3. Generate previews
4. Select slides
5. Merge presentations
6. Download result
```

---

## 13. Design Decisions

### Single Container Approach

The PoC uses a **single container** to simplify:

* environment setup
* dependency management
* execution model

All components run in the same runtime environment.

---

### File-Based Communication

Python and Node interact via:

```text
JSON files + subprocess execution
```

This avoids:

* HTTP services
* inter-process networking
* additional infrastructure

---

### Job Isolation

All processing is scoped under:

```text
/app/tmp/jobs/<job_id>
```

This ensures:

* no cross-job interference
* deterministic execution
* easy cleanup

---

## 14. Limitations

This setup is intended for a **proof of concept**.

Limitations include:

* synchronous execution
* no job queue
* no horizontal scaling
* large container size (LibreOffice)
* potential rendering differences vs PowerPoint

---

## 15. Next Steps

For production evolution, consider:

* splitting services into multiple containers
* introducing asynchronous processing
* using cloud storage (S3/GCS)
* implementing job lifecycle management
* adding monitoring and logging

---

## 16. Summary

This Docker setup provides:

```text
A fully isolated, reproducible environment
for PPTX processing, preview generation,
and slide composition in a single container.
```

It enables fast iteration and reliable execution for the PoC phase.
