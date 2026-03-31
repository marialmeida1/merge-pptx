# Architecture Overview

## Proposed target

The application is now organized around three services with one shared job volume:

```text
                        +----------------------+
                        |      Streamlit       |
User Browser ---------->|   app:8501          |
                        | orchestration + UI   |
                        +----------+-----------+
                                   |
                 +-----------------+-----------------+
                 |                                   |
                 v                                   v
      +----------------------+           +----------------------+
      |   converter:8000     |           |  merge-worker:3000   |
      | FastAPI + LibreOffice|           | Node API + Automizer |
      | PPTX -> PDF only     |           | PPTX merge only      |
      +----------+-----------+           +----------+-----------+
                 \                                   /
                  \                                 /
                   +----------- jobs-data ---------+
                               /data/jobs
```

## Why this is better

Compared to the previous single-container setup:

| Topic | Current | Proposed |
| --- | --- | --- |
| Container responsibility | UI + conversion + merge together | One concern per service |
| Streamlit image size | Large, with LibreOffice and Node | Smaller, Python + Poppler only |
| Failure blast radius | LibreOffice/Node can destabilize UI | Heavy processes isolated |
| Scaling | All-or-nothing | Converter and merge can scale independently |
| Windows + WSL2 | More sensitive to mixed runtime/process issues | Cleaner separation and named volume |
| Production readiness | PoC-style monolith container | Service-oriented and easier to operate |

## Service responsibilities

### 1. `app`

Responsibilities:

* Keep the current Streamlit flow and session state
* Manage jobs and filesystem artifacts
* Generate PNG thumbnails from PDFs
* Call auxiliary services over HTTP

What it no longer does:

* Does not ship LibreOffice
* Does not ship Node.js
* Does not run heavy office conversion locally in the container

### 2. `converter`

Responsibilities:

* Receive conversion requests over HTTP
* Run headless LibreOffice in isolation
* Write PDFs back to the shared job directory

This service exists only for preview generation.

### 3. `merge-worker`

Responsibilities:

* Receive merge requests over HTTP
* Execute the existing `pptx-automizer` worker
* Persist `merge_result.json` and the final PPTX

This keeps the current merge contract, but moves execution outside the Streamlit container.

## Communication model

The design keeps the filesystem-based job contract and adds lightweight internal HTTP between services.

### App -> Converter

* Request: `POST /convert/pptx-to-pdf`
* Payload: `job_path`, `pptx_path`
* Output: generated PDF path

### App -> Merge Worker

* Request: `POST /merge`
* Payload: `job_path`, `merge_request_path`
* Output: `merge_result.json` payload

## Shared storage

All services mount the same named Docker volume at `/data/jobs`.

Reasons:

* avoids slow bind-mounted temp directories on Windows + WSL2
* keeps paths stable across containers
* preserves the existing per-job artifact model
* makes failures easier to inspect without introducing a database yet

## Suggested project structure

```text
.
├─ app.py
├─ Dockerfile
├─ docker-compose.yml
├─ docker/
│  ├─ converter.Dockerfile
│  └─ merge-worker.Dockerfile
├─ service_apps/
│  └─ converter_api/
│     └─ main.py
├─ services/
│  ├─ preview_service.py
│  ├─ merge_service.py
│  └─ ...
├─ workers/
│  └─ node_merge/
│     ├─ merge_worker.js
│     ├─ server.js
│     └─ package.json
└─ docs/
```

## Alternatives to LibreOffice

### Best pragmatic default for now

Use a dedicated LibreOffice container, as implemented here.

Why:

* minimal application changes
* no GUI dependency
* works with Docker Desktop and WSL2
* preserves current rendering pipeline

### External APIs

Good options when reliability matters more than local control:

* CloudConvert: simplest SaaS path, broad format support
* Microsoft Graph + PowerPoint services: strongest fidelity when the source ecosystem is Microsoft 365
* Google Drive/Docs export flows: possible, but less natural for PPTX-heavy enterprise flows

Tradeoffs:

* per-document cost
* network dependency
* authentication and quotas
* data governance review

### Lighter local libraries

Pure Python alternatives are limited for faithful PPTX -> PDF rendering. In practice, they are usually not a full replacement for LibreOffice or PowerPoint-backed services.

Recommendation:

* do not replace LibreOffice with a Python-only renderer if preview fidelity matters

### Hybrid host strategy

Possible option:

* keep Streamlit in Docker
* run the converter on the host machine or a separate VM

This can work, but is less portable and more fragile for team onboarding. For Windows + WSL2, container-to-container is usually simpler than mixing host-specific office installs.

## Evolution path

If usage grows, the next pragmatic step is:

1. keep the current three services
2. add a queue for conversion and merge jobs
3. move long-running operations out of the Streamlit request path

Until then, this HTTP + shared-volume split is a good middle ground between PoC simplicity and production discipline.
