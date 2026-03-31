# Docker Setup

## Services

The stack now runs as three containers:

* `app`: Streamlit UI and orchestration
* `converter`: FastAPI + LibreOffice for `PPTX -> PDF`
* `merge-worker`: Node API + `pptx-automizer` for final merge

All three share the `jobs-data` named volume at `/data/jobs`.

## Build and run

```bash
docker compose build
docker compose up
```

App URL:

```text
http://localhost:8501
```

## Stop

```bash
docker compose down
```

To also remove the job volume:

```bash
docker compose down -v
```

## Useful commands

Check logs:

```bash
docker compose logs -f app
docker compose logs -f converter
docker compose logs -f merge-worker
```

Open shells:

```bash
docker exec -it pptx-composer-app bash
docker exec -it pptx-composer-converter bash
docker exec -it pptx-composer-merge-worker sh
```

## Windows + WSL2 notes

Recommended choices in this setup:

* use Docker named volumes for `/data/jobs`
* avoid mounting temporary job folders from the Windows filesystem
* keep LibreOffice isolated in its own Linux container
* avoid any GUI or desktop-office dependency

This reduces I/O overhead and avoids a common source of instability in mixed Windows/WSL2/container workflows.

## Container design summary

### `app` image

Contains only:

* Python
* Streamlit
* Poppler for thumbnail generation
* application source

Does not contain:

* LibreOffice
* Node.js

### `converter` image

Contains:

* Python
* FastAPI
* LibreOffice
* fonts required for more stable rendering

### `merge-worker` image

Contains:

* Node.js
* `pptx-automizer`
* a tiny HTTP wrapper for the existing merge worker

## Environment variables

Main variables used by the stack:

* `JOB_STORAGE_ROOT=/data/jobs`
* `CONVERTER_API_URL=http://converter:8000`
* `MERGE_API_URL=http://merge-worker:3000`

## Why named volumes instead of bind mounts for jobs

* better performance on Docker Desktop
* fewer file permission surprises
* stable cross-container paths
* cleaner separation between source code and runtime artifacts

## Recommended next step for production

Keep this compose layout for development and staging. If you later deploy to Kubernetes, ECS, Nomad, or similar, the same split maps cleanly to separate services with persistent shared storage or object storage.
