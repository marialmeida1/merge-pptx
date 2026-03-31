# PPTX Composer

PPTX Composer is a small document-processing application that helps users:

* upload multiple PowerPoint files (`.pptx`)
* generate visual slide previews
* select and reorder slides
* create a new merged presentation
* download the final `.pptx`

The user interface is built with Streamlit, while preview conversion and PPTX merge are isolated in dedicated services.

## What this project does

The application turns a manual presentation-composition workflow into a guided pipeline:

1. create a job
2. upload one or more PPTX files
3. convert each PPTX into PDF for preview rendering
4. generate PNG thumbnails for each slide
5. select the slides you want
6. define the final output order
7. generate a new merged PPTX
8. download the result

The project is designed to keep the main app simple while delegating heavier processing to specialized services.

## Architecture

The stack is split into three services:

* `app`: Streamlit UI and orchestration
* `converter`: FastAPI service that runs LibreOffice headlessly for `PPTX -> PDF`
* `merge-worker`: Node.js service that uses `pptx-automizer` to build the final PPTX

All services share the same Docker volume for job data.

```text
Browser
  |
  v
Streamlit app
  |----> converter API ----> LibreOffice
  |
  |----> merge-worker API -> pptx-automizer
  |
  +----> shared job storage
```

This separation makes the system lighter, more stable, and easier to scale than a single-container setup.

## Project structure

```text
.
├─ app.py
├─ Dockerfile
├─ docker-compose.yml
├─ docker/
│  ├─ converter.Dockerfile
│  └─ merge-worker.Dockerfile
├─ docs/
│  ├─ architecture.md
│  └─ docker.md
├─ service_apps/
│  └─ converter_api/
│     └─ main.py
├─ services/
│  ├─ job_service.py
│  ├─ preview_service.py
│  ├─ merge_service.py
│  ├─ selection_service.py
│  ├─ storage_service.py
│  └─ thumbnail_service.py
├─ styles/
├─ workers/
│  └─ node_merge/
│     ├─ merge_worker.js
│     ├─ server.js
│     └─ package.json
├─ requirements.txt
└─ requirements-converter.txt
```

## Main workflow

### 1. Streamlit app

The main entrypoint is [app.py](/Users/mariana/Documents/personal_study/ey-propost/app.py).

It is responsible for:

* managing session state
* creating isolated jobs
* handling file upload
* triggering preview generation
* storing selection state
* calling the merge service
* exposing the final download

### 2. Preview generation

When the user uploads PPTX files:

* the files are saved into the current job directory
* the app calls the converter API
* the converter runs LibreOffice in headless mode and generates PDFs
* the app converts each PDF page into PNG thumbnails using `pdf2image`

Relevant files:

* [services/storage_service.py](/Users/mariana/Documents/personal_study/ey-propost/services/storage_service.py)
* [services/preview_service.py](/Users/mariana/Documents/personal_study/ey-propost/services/preview_service.py)
* [services/thumbnail_service.py](/Users/mariana/Documents/personal_study/ey-propost/services/thumbnail_service.py)
* [service_apps/converter_api/main.py](/Users/mariana/Documents/personal_study/ey-propost/service_apps/converter_api/main.py)

### 3. Slide selection

After previews are generated, the user can:

* inspect slides visually
* select slides from different presentations
* reorder the selected slides

The selection is normalized and saved as a merge request.

Relevant file:

* [services/selection_service.py](/Users/mariana/Documents/personal_study/ey-propost/services/selection_service.py)

### 4. Final merge

The app writes a `merge_request.json` file and sends it to the Node.js merge service.

The merge service:

* reads the merge request
* loads source presentations
* copies the selected slides in order
* writes the final PPTX to the output directory
* persists `merge_result.json`

Relevant files:

* [services/merge_service.py](/Users/mariana/Documents/personal_study/ey-propost/services/merge_service.py)
* [workers/node_merge/server.js](/Users/mariana/Documents/personal_study/ey-propost/workers/node_merge/server.js)
* [workers/node_merge/merge_worker.js](/Users/mariana/Documents/personal_study/ey-propost/workers/node_merge/merge_worker.js)

## Requirements

Recommended:

* Docker Desktop
* Docker Compose v2

You do not need LibreOffice or Node.js installed on your host if you run the stack with Docker.

## Quick start

### 1. Build the services

```bash
docker compose build
```

### 2. Start the stack

```bash
docker compose up
```

### 3. Open the app

Open:

```text
http://localhost:8501
```

### 4. Use the application

Inside the UI:

1. click `Criar novo job`
2. upload one or more `.pptx` files
3. wait for preview generation
4. select and reorder slides
5. run the merge
6. download the generated presentation

## Running in background

```bash
docker compose up -d
```

To inspect logs:

```bash
docker compose logs -f app
docker compose logs -f converter
docker compose logs -f merge-worker
```

To stop everything:

```bash
docker compose down
```

To also remove the shared job volume:

```bash
docker compose down -v
```

## Environment variables

These are the main service-level variables used in the Docker setup:

* `JOB_STORAGE_ROOT=/data/jobs`
* `CONVERTER_API_URL=http://converter:8000`
* `MERGE_API_URL=http://merge-worker:3000`
* `STREAMLIT_SERVER_ADDRESS=0.0.0.0`
* `STREAMLIT_SERVER_PORT=8501`

## Job storage

Each run is isolated in its own job directory under the shared volume.

Typical structure:

```text
job/
├─ inputs/
├─ previews/
├─ outputs/
├─ metadata.json
├─ selection.json
├─ merge_request.json
└─ merge_result.json
```

This keeps processing traceable and avoids collisions between runs.

## Why the services are separated

The original all-in-one container approach made the app heavier and less stable because it mixed:

* Streamlit UI
* LibreOffice-based conversion
* Node-based PPTX merge

The current design improves that by:

* keeping the app container lighter
* isolating LibreOffice crashes from the UI
* isolating merge execution from the UI
* making future scaling easier
* reducing responsibility overlap inside a single container

## Troubleshooting

### Docker build fails during `apt-get update`

This usually indicates a Docker networking or DNS issue, not an application bug.

Useful checks:

```bash
curl -I https://registry-1.docker.io/v2/
docker pull busybox:latest
docker run --rm python:3.11-slim-bookworm sh -c "apt-get update"
```

If those fail, inspect:

* Docker Desktop network settings
* proxy configuration
* VPN interference
* local firewall rules

### App starts but previews fail

Check converter logs:

```bash
docker compose logs -f converter
```

### App starts but merge fails

Check merge worker logs:

```bash
docker compose logs -f merge-worker
```

## Documentation

Additional documentation is available here:

* [docs/architecture.md](/Users/mariana/Documents/personal_study/ey-propost/docs/architecture.md)
* [docs/docker.md](/Users/mariana/Documents/personal_study/ey-propost/docs/docker.md)
* [docs/workflow_overview.md](/Users/mariana/Documents/personal_study/ey-propost/docs/workflow_overview.md)

## Current status

This project is intentionally pragmatic:

* filesystem-based job storage
* synchronous processing flow
* no queue yet
* no database yet

That keeps the implementation simple while still being much closer to a production-shaped architecture than a single monolithic container.
