# Technical Guidance Document — Phase 5

## Final Delivery, Download Handling, Cleanup Strategy, and End-to-End PoC Hardening

---

## 1. Objective

Complete the PoC by introducing the final user-facing and operational capabilities required for an end-to-end usable workflow.

This phase must ensure that the system can:

* Expose the generated `.pptx` file for download in Streamlit
* Surface success and failure states clearly to the user
* Manage the lifecycle of job artifacts
* Provide a minimal cleanup strategy for temporary files
* Validate the full workflow from upload to final composed presentation

This phase intentionally excludes:

* distributed processing
* background workers
* queue-based orchestration
* cloud storage
* authentication and authorization
* production-grade monitoring and metrics

---

## 2. Scope

This phase begins after the final `.pptx` has been successfully generated in Phase 4.

The system must support the following sequence:

1. Detect that a valid output file exists
2. Present the output artifact to the user
3. Allow the user to download the final `.pptx`
4. Surface structured failure states when any phase fails
5. Allow job reset or cleanup
6. Support repeatable end-to-end PoC execution

---

## 3. Final Workflow Definition

At the end of Phase 5, the full system must support this complete pipeline:

```text
Job creation
-> PPTX upload
-> Preview generation
-> Slide selection
-> Slide ordering
-> Merge request generation
-> Node worker execution
-> Final PPTX generation
-> Download
-> Cleanup or reset
```

This becomes the canonical PoC flow.

---

## 4. User Experience Requirements

The Streamlit application must provide a coherent end-to-end experience.

### Required user-visible states

* No job exists
* Job created, no files uploaded
* Files uploaded, previews not yet generated
* Previews generated, no slides selected
* Slides selected, merge request ready
* Merge in progress
* Merge completed successfully
* Merge failed
* Download available
* Job reset or cleaned

### Design rule

The UI must always reflect the current processing state of the active job.

No hidden or ambiguous state transitions are allowed.

---

## 5. Directory Structure

No major structural changes are required, but the job artifact lifecycle must now be fully defined.

```text
project/
├─ app.py
├─ services/
│  ├─ job_service.py
│  ├─ storage_service.py
│  ├─ preview_service.py
│  ├─ thumbnail_service.py
│  ├─ selection_service.py
│  ├─ merge_service.py
│  └─ cleanup_service.py
├─ workers/
│  └─ node_merge/
├─ tmp/
│  └─ jobs/
│     └─ job_<id>/
│        ├─ inputs/
│        ├─ outputs/
│        │  └─ final.pptx
│        ├─ previews/
│        ├─ selection.json
│        ├─ merge_request.json
│        ├─ merge_result.json
│        └─ metadata.json
└─ requirements.txt
```

---

## 6. Component Responsibilities

### 6.1 Streamlit Layer

Responsibilities:

* Display full workflow status
* Expose final download control
* Surface errors clearly
* Allow job reset or cleanup

Constraints:

* UI must not perform direct filesystem deletion
* Cleanup actions must be delegated to a service layer

---

### 6.2 Cleanup Service

File: `services/cleanup_service.py`

Responsibilities:

* Remove a specific job directory
* Reset session state for a new run
* Support optional selective cleanup

Constraints:

* Must only delete paths under the job root
* Must fail safely
* Must not allow arbitrary path deletion

---

### 6.3 Merge and Output Validation Layer

Responsibilities:

* Verify that output artifact exists
* Verify that output artifact is readable
* Confirm that downstream download can be offered safely

Constraints:

* Must not mark a run as successful unless the file exists
* Must not expose a broken or missing artifact to the user

---

## 7. State Model

The application should treat the job as progressing through explicit phases.

### Recommended state progression

```text
created
-> files_uploaded
-> previews_ready
-> selection_ready
-> merge_ready
-> merged
-> downloadable
-> cleaned
```

This does not require a database; it can be derived from artifacts and session state.

### Minimum requirement

The UI must be able to infer whether:

* previews exist
* selection exists
* merge request exists
* merge result exists
* final output exists

---

## 8. Output Delivery Requirements

The final output must be delivered through Streamlit’s download mechanism.

### Required behavior

* The application must open the generated `.pptx` in binary mode
* The correct MIME type must be provided
* The download filename must be deterministic

### Example MIME type

```text
application/vnd.openxmlformats-officedocument.presentationml.presentation
```

### Example filename

```text
final_<job_id>.pptx
```

---

## 9. Cleanup Strategy

This PoC requires a minimal but explicit cleanup strategy.

### Supported cleanup actions

1. **Reset current job in UI**

   * Clear session state
   * Keep filesystem artifacts temporarily

2. **Delete current job artifacts**

   * Remove job directory recursively
   * Clear session state

### Design recommendation

Expose both actions separately if useful, but for a PoC a single “Delete current job and reset” action is sufficient.

### Constraints

* Cleanup must be explicit, not automatic
* No background sweeper is required in this phase
* No TTL-based deletion is required

---

## 10. Implementation Specification

### 10.1 Cleanup Service

File: `services/cleanup_service.py`

```python
import shutil
from pathlib import Path


def delete_job_directory(job_path: Path):
    base_jobs_dir = Path("tmp/jobs").resolve()
    resolved_job_path = job_path.resolve()

    if base_jobs_dir not in resolved_job_path.parents:
        raise ValueError(f"Refusing to delete non-job path: {resolved_job_path}")

    if resolved_job_path.exists():
        shutil.rmtree(resolved_job_path)
```

---

### 10.2 Session Reset Helper

This helper clears application state after cleanup or restart.

```python
import streamlit as st


def reset_job_session_state():
    keys_to_clear = [
        "job_id",
        "job_path",
        "previews",
        "selected_identities",
        "ordered_identities",
        "normalized_selection",
        "merge_request",
        "merge_result",
        "final_output_path",
    ]

    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
```

---

## 11. Streamlit Download Integration

The application must only expose download when a validated final output exists.

### Example

```python
from pathlib import Path
import streamlit as st

if "final_output_path" in st.session_state and st.session_state.final_output_path:
    output_path = Path(st.session_state.final_output_path)

    if output_path.exists():
        with open(output_path, "rb") as f:
            st.download_button(
                label="Download final PPTX",
                data=f,
                file_name=f"final_{st.session_state.job_id}.pptx",
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            )
    else:
        st.error("The final PPTX was expected but is missing.")
```

---

## 12. Streamlit Cleanup Integration

The UI must expose explicit cleanup/reset controls.

### Example

```python
import streamlit as st
from services.cleanup_service import delete_job_directory
from services.cleanup_service import reset_job_session_state

if st.session_state.get("job_path"):
    if st.button("Delete current job and reset"):
        try:
            delete_job_directory(st.session_state.job_path)
            reset_job_session_state()
            st.success("Current job deleted and session reset.")
            st.rerun()
        except Exception as e:
            st.error(f"Cleanup failed: {e}")
```

---

## 13. Error Presentation Requirements

The UI must clearly communicate errors from all prior phases.

### Minimum categories

* Upload failure
* Preview generation failure
* Selection validation failure
* Merge request generation failure
* Node worker failure
* Output validation failure
* Download artifact missing
* Cleanup failure

### Design rule

Each error must be:

* visible
* contextual
* actionable where possible

### Example

Instead of:

```text
Error
```

Prefer:

```text
Preview generation failed for deck_a.pptx because LibreOffice did not produce a PDF artifact.
```

---

## 14. End-to-End Validation Strategy

This phase must include manual validation of the complete PoC.

### Required test scenarios

#### Scenario 1 — Happy path

* Create job
* Upload multiple PPTX files
* Generate previews
* Select slides from multiple presentations
* Order slides
* Generate merge request
* Execute merge
* Download final PPTX

#### Scenario 2 — Missing source file before merge

* Upload files
* Generate previews
* Remove one source file manually
* Attempt merge
* Confirm explicit failure

#### Scenario 3 — No slides selected

* Upload files
* Generate previews
* Attempt merge request generation without selection
* Confirm validation block

#### Scenario 4 — Worker failure propagation

* Simulate a bad merge request
* Confirm Python surfaces Node stderr cleanly

#### Scenario 5 — Cleanup

* Run a full job
* Delete the job
* Confirm the directory is removed
* Confirm the UI resets cleanly

---

## 15. Success Criteria

This phase is considered complete when:

* The final PPTX can be downloaded through Streamlit
* Success and failure states are clearly represented in the UI
* The current job can be explicitly cleaned
* Session state resets correctly after cleanup
* The end-to-end workflow can be executed repeatedly without cross-job contamination

---

## 16. Operational Constraints

* All processing remains synchronous
* Temporary files remain local to the application environment
* No automatic garbage collection is required
* No concurrent job scheduling is introduced
* The PoC assumes a trusted local execution environment

---

## 17. Architectural Decisions

* Output delivery remains inside Streamlit
* Cleanup is explicit rather than automatic
* Filesystem remains the authoritative artifact store
* Job state is inferred from artifacts and session state
* End-to-end usability is prioritized over production-grade infrastructure

---

## 18. Final Exit Criteria

The PoC is considered complete when the system reliably supports:

```text
Upload -> Preview -> Select -> Order -> Merge -> Download -> Cleanup
```

with all operations scoped to a job-isolated filesystem structure and coordinated through the Streamlit/Python application.

---

## 19. Final Notes

At the conclusion of this phase, the system will have reached its intended PoC state:

* Python remains the orchestration layer
* Streamlit remains the user interface
* LibreOffice remains the preview engine
* Node.js remains the specialized slide composition engine
* filesystem-based job isolation remains the execution boundary

This is sufficient for a technical proof of concept and creates a stable base for future evolution into:

* containerized deployment
* asynchronous execution
* persistent storage
* better observability
* stronger validation and resilience
