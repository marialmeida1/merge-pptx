## Slide Preview Generation with LibreOffice Headless and Python

## 1. Objective

Extend the application foundation to support **slide preview generation** for uploaded `.pptx` files.

This phase must introduce a deterministic pipeline that:

* Converts uploaded `.pptx` files into `.pdf`
* Renders one image per PDF page
* Associates each rendered image with a slide index
* Exposes slide previews in Streamlit

---

## 2. Scope

For each uploaded `.pptx` inside a job:

1. Read the file from the job input directory
2. Convert the file to PDF using LibreOffice in headless mode
3. Convert each PDF page into an image
4. Save the generated thumbnails under the job directory
5. Return structured preview metadata to the UI layer

---

## 3. Processing Model

The preview pipeline must be treated as a **derived artifact generation phase**.

### Input

```text
job/<id>/inputs/<presentation>.pptx
```

### Derived outputs

```text
job/<id>/previews/<presentation>.pdf
job/<id>/previews/<presentation>/slide-1.png
job/<id>/previews/<presentation>/slide-2.png
...
```

### Metadata output

A structured preview manifest must be produced so the UI can render thumbnails deterministically.

---

## 4. Directory Structure

The job structure must now evolve to include preview artifacts:

```text
project/
├─ app.py
├─ services/
│  ├─ job_service.py
│  ├─ storage_service.py
│  ├─ preview_service.py
│  └─ thumbnail_service.py
├─ tmp/
│  └─ jobs/
│     └─ job_<id>/
│        ├─ inputs/
│        ├─ outputs/
│        ├─ previews/
│        │  ├─ presentation_a.pdf
│        │  ├─ presentation_a/
│        │  │  ├─ slide-1.png
│        │  │  ├─ slide-2.png
│        │  │  └─ ...
│        │  └─ presentation_b/
│        └─ metadata.json
└─ requirements.txt
```

### Constraints

* Preview artifacts must remain scoped to the job
* No preview files may be written outside the job directory
* Preview generation must be repeatable without cross-job side effects

---

## 5. Dependencies

This phase introduces native and Python-level dependencies.

### Python dependencies

```text
streamlit
pdf2image
```

### Native dependencies

* LibreOffice
* Poppler utilities

### Notes

* LibreOffice is required for `.pptx -> .pdf`
* Poppler is required by `pdf2image` for `.pdf -> .png`

---

## 6. Component Responsibilities

### 6.1 Streamlit Layer

Responsibilities:

* Trigger preview generation
* Display generated thumbnails
* Render previews grouped by source presentation

Constraints:

* The UI must not execute conversion logic directly
* The UI must only consume structured preview metadata

---

### 6.2 Preview Service

File: `services/preview_service.py`

Responsibilities:

* Convert `.pptx` into `.pdf` using LibreOffice CLI
* Create preview directories
* Validate that conversion produced expected output

Constraints:

* Must use subprocess execution
* Must fail explicitly if PDF generation does not succeed
* Must not embed business logic unrelated to conversion

---

### 6.3 Thumbnail Service

File: `services/thumbnail_service.py`

Responsibilities:

* Convert generated PDF pages into PNG images
* Maintain deterministic slide-to-image mapping
* Return structured slide preview metadata

Constraints:

* Image naming must be stable and index-based
* Slide numbering must be explicit and consistent

---

## 7. Processing Pipeline

The implementation must follow this exact sequence:

```text
1. Read PPTX from job input directory
2. Convert PPTX to PDF using LibreOffice headless
3. Create a preview folder for the source presentation
4. Convert PDF pages to PNG images
5. Return structured preview metadata
```

---

## 8. Implementation Specification

### 8.1 Preview Service

File: `services/preview_service.py`

```python
import subprocess
from pathlib import Path


def convert_pptx_to_pdf(job_path: Path, pptx_path: Path) -> Path:
    previews_dir = job_path / "previews"
    previews_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "soffice",
        "--headless",
        "--convert-to",
        "pdf",
        "--outdir",
        str(previews_dir),
        str(pptx_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(
            f"LibreOffice conversion failed for {pptx_path.name}: {result.stderr}"
        )

    pdf_path = previews_dir / f"{pptx_path.stem}.pdf"

    if not pdf_path.exists():
        raise FileNotFoundError(
            f"Expected PDF was not generated: {pdf_path}"
        )

    return pdf_path
```

---

### 8.2 Thumbnail Service

File: `services/thumbnail_service.py`

```python
from pathlib import Path
from pdf2image import convert_from_path


def generate_thumbnails(job_path: Path, pdf_path: Path):
    presentation_preview_dir = job_path / "previews" / pdf_path.stem
    presentation_preview_dir.mkdir(parents=True, exist_ok=True)

    pages = convert_from_path(str(pdf_path), dpi=120)

    slides = []

    for index, page in enumerate(pages, start=1):
        image_path = presentation_preview_dir / f"slide-{index}.png"
        page.save(image_path, "PNG")

        slides.append({
            "slide_index": index,
            "image_path": str(image_path),
        })

    return {
        "presentation_name": pdf_path.stem,
        "pdf_path": str(pdf_path),
        "slides": slides,
    }
```

---

### 8.3 Orchestration Helper

This helper coordinates preview generation for all uploaded PPTX files.

File: `services/preview_service.py`

```python
from pathlib import Path
from services.thumbnail_service import generate_thumbnails


def generate_previews_for_job(job_path: Path):
    input_dir = job_path / "inputs"
    pptx_files = list(input_dir.glob("*.pptx"))

    previews = []

    for pptx_file in pptx_files:
        pdf_path = convert_pptx_to_pdf(job_path, pptx_file)
        preview_manifest = generate_thumbnails(job_path, pdf_path)
        previews.append(preview_manifest)

    return previews
```

---

## 9. Streamlit Integration

The UI must expose a user-triggered action for preview generation.

Example integration:

```python
import streamlit as st
from pathlib import Path

from services.job_service import create_job
from services.storage_service import save_uploaded_files, list_files
from services.preview_service import generate_previews_for_job

st.set_page_config(page_title="PPTX Composer", layout="wide")
st.title("PPTX Composer — PoC")

if "job_id" not in st.session_state:
    st.session_state.job_id = None
    st.session_state.job_path = None
    st.session_state.previews = None

if st.button("Create new job"):
    job_id, job_path = create_job()
    st.session_state.job_id = job_id
    st.session_state.job_path = job_path
    st.session_state.previews = None

    st.success(f"Job created: {job_id}")

if st.session_state.job_id:
    uploaded_files = st.file_uploader(
        "Upload PPTX files",
        type=["pptx"],
        accept_multiple_files=True
    )

    if uploaded_files:
        saved = save_uploaded_files(st.session_state.job_path, uploaded_files)
        st.success(f"{len(saved)} files uploaded successfully")

if st.session_state.job_id:
    files = list_files(st.session_state.job_path)

    if files:
        st.subheader("Uploaded files")
        for f in files:
            st.write(f)

        if st.button("Generate previews"):
            st.session_state.previews = generate_previews_for_job(
                st.session_state.job_path
            )

if st.session_state.previews:
    st.subheader("Slide previews")

    for presentation in st.session_state.previews:
        st.markdown(f"### {presentation['presentation_name']}")

        cols = st.columns(4)
        for i, slide in enumerate(presentation["slides"]):
            with cols[i % 4]:
                st.image(slide["image_path"], caption=f"Slide {slide['slide_index']}")
```

---

## 10. Expected Output Structure

The preview generation phase must return data in a structure similar to:

```json
{
  "presentation_name": "deck_a",
  "pdf_path": "tmp/jobs/job_123/previews/deck_a.pdf",
  "slides": [
    {
      "slide_index": 1,
      "image_path": "tmp/jobs/job_123/previews/deck_a/slide-1.png"
    },
    {
      "slide_index": 2,
      "image_path": "tmp/jobs/job_123/previews/deck_a/slide-2.png"
    }
  ]
}
```

This structure must be stable because subsequent phases will consume slide indices from it.

---

## 11. Validation Criteria

This phase is considered complete when:

* Uploaded `.pptx` files can be converted to `.pdf`
* PDF pages can be converted into PNG images
* Slide indices are correctly mapped to thumbnail paths
* Streamlit displays the generated thumbnails
* All artifacts remain isolated under the job directory

---

## 12. Error Handling Requirements

The implementation must explicitly handle the following cases:

### Conversion failure

If LibreOffice fails:

* raise an explicit error
* identify the failing file
* do not silently continue

### Missing PDF output

If the CLI returns successfully but no PDF is created:

* raise `FileNotFoundError`

### Thumbnail generation failure

If PDF rendering fails:

* stop processing for that file
* surface the error to the UI

### UI behavior

The UI should display:

* success state when previews are available
* failure state with an actionable error message when generation fails

---

## 13. Constraints and Assumptions

* Preview fidelity is not guaranteed to exactly match Microsoft PowerPoint rendering
* This phase assumes valid `.pptx` inputs
* No caching layer is implemented
* Re-generating previews may overwrite previous preview files for the same job
* No background processing or queueing is introduced in this phase

---

## 14. Architectural Decisions

* LibreOffice is used strictly as a conversion engine
* PDF is used as the intermediate rendering format
* PNG is used for deterministic thumbnail output
* Streamlit remains the presentation layer only
* Preview generation remains synchronous for simplicity

---

## 15. Exit Criteria

This phase is complete when the system reliably supports:

```text
PPTX -> PDF -> PNG previews -> Streamlit rendering
```

with all generated artifacts scoped inside the job directory.

---

## 16. Next Phase

Phase 3 will introduce:

* slide selection in the UI
* selection state management
* ordering of selected slides
* generation of a merge request payload for downstream composition

This phase will consume the preview metadata generated here without requiring structural changes to the preview pipeline.
