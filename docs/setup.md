## Streamlit Application Setup and PPTX Upload Handling

## 1. Objective

Establish the foundational structure of the application to support:

* Multi-file `.pptx` upload via Streamlit
* Temporary storage of uploaded files
* Isolation of processing context using a job-based model
* Preparation for subsequent phases (preview generation and slide merging)

## 2. Core Concept: Job-Based Isolation

Each user interaction is encapsulated within a **job**, which serves as a processing boundary.

### Definition

A job represents a unit of work containing:

* Uploaded input files
* Intermediate artifacts (future phases)
* Output artifacts (future phases)

### Requirements

* Each job must have a unique identifier
* All files must be scoped to a single job directory
* Jobs must be stateless beyond filesystem persistence

---

## 3. Directory Structure

The system must enforce the following structure:

```text
project/
├─ app.py
├─ services/
│  ├─ job_service.py
│  └─ storage_service.py
├─ tmp/
│  └─ jobs/
│     └─ job_<id>/
│        ├─ inputs/
│        ├─ outputs/
│        └─ metadata.json
└─ requirements.txt
```

### Constraints

* All uploaded files must reside under `inputs/`
* No cross-job file access is permitted
* The filesystem acts as the only persistence layer in this phase

---

## 4. Dependencies

The following minimal dependencies are required:

```text
streamlit
```

Standard library modules:

* `uuid`
* `pathlib`

No additional dependencies should be introduced at this stage.

---

## 5. Component Responsibilities

### 5.1 Streamlit Layer

Responsibilities:

* Trigger job creation
* Accept multiple `.pptx` uploads
* Display uploaded file list
* Maintain session state

Constraints:

* No business logic should be embedded directly in the UI
* All file operations must be delegated to service layers

---

### 5.2 Job Service

File: `services/job_service.py`

Responsibilities:

* Generate unique job identifiers
* Create directory structure
* Initialize metadata

Constraints:

* Must be deterministic and idempotent per invocation
* Must not depend on external systems

---

### 5.3 Storage Service

File: `services/storage_service.py`

Responsibilities:

* Persist uploaded files to disk
* Provide file listing capabilities

Constraints:

* Must not modify file contents
* Must not perform validation at this stage

---

## 6. Implementation Specification

### 6.1 Job Service

```python
import uuid
from pathlib import Path

BASE_DIR = Path("tmp/jobs")

def create_job():
    job_id = f"job_{uuid.uuid4().hex[:8]}"
    job_path = BASE_DIR / job_id

    (job_path / "inputs").mkdir(parents=True, exist_ok=True)
    (job_path / "outputs").mkdir(parents=True, exist_ok=True)

    metadata = {
        "job_id": job_id,
        "files": []
    }

    (job_path / "metadata.json").write_text(str(metadata))

    return job_id, job_path
```

---

### 6.2 Storage Service

```python
from pathlib import Path

def save_uploaded_files(job_path: Path, uploaded_files):
    saved_files = []

    input_dir = job_path / "inputs"

    for file in uploaded_files:
        file_path = input_dir / file.name

        with open(file_path, "wb") as f:
            f.write(file.getbuffer())

        saved_files.append({
            "filename": file.name,
            "path": str(file_path)
        })

    return saved_files


def list_files(job_path: Path):
    input_dir = job_path / "inputs"
    return [f.name for f in input_dir.glob("*.pptx")]
```

---

### 6.3 Streamlit Application

```python
import streamlit as st

from services.job_service import create_job
from services.storage_service import save_uploaded_files, list_files

st.set_page_config(page_title="PPTX Composer", layout="wide")

st.title("PPTX Composer — PoC")

# Initialize session state
if "job_id" not in st.session_state:
    st.session_state.job_id = None
    st.session_state.job_path = None

# Create job
if st.button("Create new job"):
    job_id, job_path = create_job()
    st.session_state.job_id = job_id
    st.session_state.job_path = job_path

    st.success(f"Job created: {job_id}")

# Upload files
if st.session_state.job_id:
    uploaded_files = st.file_uploader(
        "Upload PPTX files",
        type=["pptx"],
        accept_multiple_files=True
    )

    if uploaded_files:
        saved = save_uploaded_files(st.session_state.job_path, uploaded_files)
        st.success(f"{len(saved)} files uploaded successfully")

# List files
if st.session_state.job_id:
    files = list_files(st.session_state.job_path)

    if files:
        for f in files:
            st.write(f)
    else:
        st.info("No files uploaded")
```

---

## 7. Execution Flow

```text
1. User initializes a new job
2. System generates a unique job identifier
3. Directory structure is created
4. User uploads one or more PPTX files
5. Files are persisted under job-specific input directory
6. UI reflects current job state and file list
```

---

## 8. Validation Criteria

The implementation is considered complete when:

* A job can be created deterministically
* Multiple `.pptx` files can be uploaded
* Files are persisted in the correct directory
* Files are retrievable and listed in the UI
* No cross-job contamination occurs

---

## 9. Constraints and Assumptions

* File name collisions are not handled in this phase
* File validation is out of scope
* No persistence beyond local filesystem
* No concurrency control required
* No cleanup strategy implemented

---

## 10. Architectural Decisions

* Local filesystem used for storage due to simplicity and speed
* Streamlit session state used for job tracking
* Separation of concerns enforced via service layer
* No external dependencies introduced

---

## 11. Exit Criteria

This phase is complete when the system reliably supports:

```text
Upload → Storage → Retrieval
```

and provides a stable foundation for:

* slide preview generation
* user-driven slide selection
* downstream merge processing

---

## 12. Next Phase

Phase 2 will introduce:

* LibreOffice headless execution
* PPTX to PDF conversion
* PDF to image transformation
* Slide thumbnail rendering in Streamlit

This will extend the current job structure without requiring architectural changes.
