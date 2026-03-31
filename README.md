# PPTX Composer

PPTX Composer is a containerized application for building a new PowerPoint deck from slides selected across multiple `.pptx` files.

It gives users a simple visual workflow:

* upload multiple presentations
* generate slide previews
* select and reorder slides
* generate a merged presentation
* download the final `.pptx`

The project is built as a pragmatic PoC with a cleaner service split than the original single-container approach.

> Status: active PoC with a production-oriented architecture baseline

## Why this project

The initial version placed Streamlit, LibreOffice, preview generation, and the Node.js merge worker in a single container. That worked for a first prototype, but it also made the setup heavier, harder to maintain, and more fragile.

This version keeps the same core user flow while separating the heavy processing steps into dedicated services.

## Key features

* Visual slide preview generation from uploaded PPTX files
* Slide selection across multiple presentations
* Slide ordering before final composition
* PPTX merge powered by `pptx-automizer`
* Headless conversion pipeline for preview rendering
* Docker-based multi-service setup
* Job-based filesystem isolation for traceability

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

This separation makes the system lighter, more stable, and easier to evolve than the original all-in-one container.

## Main workflow

1. Create a new job.
2. Upload one or more `.pptx` files.
3. Convert each PPTX to PDF for preview rendering.
4. Generate PNG thumbnails from the PDF pages.
5. Select the slides to keep.
6. Reorder the selected slides.
7. Build the merge request.
8. Generate the final PPTX.
9. Download the result.

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
│  ├─ docker.md
│  ├─ poc_validation.md
│  └─ workflow_overview.md
├─ service_apps/
│  └─ converter_api/
│     └─ main.py
├─ services/
│  ├─ job_service.py
│  ├─ merge_service.py
│  ├─ preview_service.py
│  ├─ selection_service.py
│  ├─ storage_service.py
│  └─ thumbnail_service.py
├─ styles/
├─ workers/
│  └─ node_merge/
│     ├─ merge_worker.js
│     ├─ package.json
│     └─ server.js
├─ requirements.txt
└─ requirements-converter.txt
```

## Core components

### Streamlit app

The main entrypoint is [app.py](app.py).

Responsibilities:

* manage session state
* create isolated jobs
* handle file upload
* trigger preview generation
* track slide selection and ordering
* call the merge service
* expose the final download

### Preview generation

When the user uploads PPTX files:

* files are saved into the current job directory
* the app calls the converter API
* the converter runs LibreOffice in headless mode and generates PDFs
* the app converts each PDF page into PNG thumbnails using `pdf2image`

Relevant files:

* [services/storage_service.py](services/storage_service.py)
* [services/preview_service.py](services/preview_service.py)
* [services/thumbnail_service.py](services/thumbnail_service.py)
* [service_apps/converter_api/main.py](service_apps/converter_api/main.py)

### Slide selection

After previews are generated, the user can inspect, select, and reorder slides. The resulting state is normalized and stored as a merge request.

Relevant file:

* [services/selection_service.py](services/selection_service.py)

### Final merge

The app writes a `merge_request.json` file and sends it to the Node.js merge service.

The merge service:

* reads the merge request
* loads source presentations
* copies the selected slides in order
* writes the final PPTX to the output directory
* persists `merge_result.json`

Relevant files:

* [services/merge_service.py](services/merge_service.py)
* [workers/node_merge/server.js](workers/node_merge/server.js)
* [workers/node_merge/merge_worker.js](workers/node_merge/merge_worker.js)

## Requirements

Recommended:

* Docker Desktop
* Docker Compose v2

You do not need LibreOffice or Node.js installed locally if you run the stack with Docker.

## Quick start

Build the services:

```bash
docker compose build
```

Start the stack:

```bash
docker compose up
```

Open the application:

```text
http://localhost:8501
```

Inside the UI:

1. Click `Criar novo job`.
2. Upload one or more `.pptx` files.
3. Wait for preview generation.
4. Select and reorder slides.
5. Run the merge.
6. Download the generated presentation.

## Useful commands

Run in background:

```bash
docker compose up -d
```

Inspect logs:

```bash
docker compose logs -f app
docker compose logs -f converter
docker compose logs -f merge-worker
```

Stop the stack:

```bash
docker compose down
```

Stop and remove the shared volume:

```bash
docker compose down -v
```

## Environment variables

Main service-level variables used in the Docker setup:

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

## Tradeoffs

This project intentionally favors simplicity over completeness at this stage.

Current tradeoffs:

* LibreOffice is still used for preview conversion, even though it is a heavy dependency
* processing is still synchronous
* jobs are stored on a shared Docker volume instead of external storage
* there is no queue, database, or advanced retry strategy yet

That said, the architecture is already much cleaner and easier to evolve than a monolithic container.

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

Additional project documentation:

* [docs/architecture.md](docs/architecture.md)
* [docs/docker.md](docs/docker.md)
* [docs/poc_validation.md](docs/poc_validation.md)
* [docs/workflow_overview.md](docs/workflow_overview.md)

## Future improvements

Natural next steps for this project:

* add healthchecks and readiness checks
* move conversion and merge to asynchronous jobs
* adopt external storage for artifacts
* improve observability with structured logs and metrics
* add integration tests for the end-to-end workflow

## License

Add your preferred license here before publishing publicly.
