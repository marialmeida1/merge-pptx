## Node.js Worker Integration and Final PPTX Composition

## 1. Objective

Extend the application to support **actual PPTX composition** by integrating a dedicated Node.js worker responsible for:

* Reading the merge request generated in Phase 3
* Loading source `.pptx` files
* Copying the selected slides in the defined order
* Generating the final composed `.pptx`
* Returning execution results to the Python application

This phase must introduce a clear execution boundary between:

* the **Python/Streamlit orchestration layer**
* the **Node.js PPTX composition engine**

This phase intentionally excludes:

* advanced retry logic
* asynchronous job queueing
* distributed execution
* cloud storage integration
* production-grade observability

---

## 2. Scope

This phase begins when a valid merge request exists.

The system must support the following sequence:

1. Read the normalized merge request payload
2. Transform the payload into the Node worker input contract
3. Execute the Node worker from Python
4. Compose the final `.pptx`
5. Persist the result inside the job output directory
6. Return structured execution metadata to the UI

---

## 3. Architectural Role of the Node Worker

The Node worker exists to solve the part of the workflow that Python should not own in this PoC:

* copying slides between existing PPTX files
* preserving presentation structure as well as possible
* composing a new PPTX from multiple existing decks

### Design rule

The Node worker must be treated as an **internal composition engine**, not as a separate application layer.

For this phase, the integration model is:

```text
Streamlit UI
    -> Python orchestration
        -> subprocess execution
            -> Node.js merge worker
                -> final.pptx
```

---

## 4. Execution Boundary

The Python application remains the system entry point.

### Python responsibilities

* validate that merge request exists
* prepare worker input payload
* invoke the Node worker
* interpret worker result
* expose success or failure to the UI
* make the generated `.pptx` available for download

### Node responsibilities

* receive worker input
* group requested slides by source presentation
* load source PPTX files
* add the selected slides to a new output presentation in the requested order
* write the final `.pptx`
* emit structured execution result

---

## 5. Directory Structure

The project must now include the Node worker and worker-related artifacts.

```text
project/
├─ app.py
├─ services/
│  ├─ job_service.py
│  ├─ storage_service.py
│  ├─ preview_service.py
│  ├─ thumbnail_service.py
│  ├─ selection_service.py
│  └─ merge_service.py
├─ workers/
│  └─ node_merge/
│     ├─ package.json
│     ├─ merge_worker.js
│     └─ node_modules/
├─ tmp/
│  └─ jobs/
│     └─ job_<id>/
│        ├─ inputs/
│        ├─ outputs/
│        │  └─ final.pptx
│        ├─ previews/
│        ├─ selection.json
│        ├─ merge_request.json
│        └─ merge_result.json
└─ requirements.txt
```

### Constraints

* Worker input and output artifacts must remain job-scoped
* Python and Node must communicate through explicit payload files and structured stdout/stderr
* The Node worker must never read outside the declared job payload

---

## 6. Worker Communication Model

For this PoC, communication must use **file-based JSON payloads + subprocess invocation**.

### Rationale

This is the lowest-complexity option because it avoids:

* HTTP service bootstrapping
* inter-service authentication
* API lifecycle management
* additional infrastructure

### Communication pattern

```text
Python writes merge_request.json
    -> Python executes node merge_worker.js <merge_request.json>
        -> Node reads request
        -> Node generates final.pptx
        -> Node writes merge_result.json
        -> Node prints status to stdout
```

---

## 7. Worker Input Contract

The Node worker must consume a payload with a deterministic structure.

### Canonical input

```json
{
  "job_id": "job_123",
  "output": "tmp/jobs/job_123/outputs/final.pptx",
  "selection": [
    {
      "selection_id": "sel_a1b2c3d4",
      "presentation_name": "deck_a",
      "presentation_path": "tmp/jobs/job_123/inputs/deck_a.pptx",
      "slide_index": 2,
      "output_position": 1
    },
    {
      "selection_id": "sel_e5f6g7h8",
      "presentation_name": "deck_c",
      "presentation_path": "tmp/jobs/job_123/inputs/deck_c.pptx",
      "slide_index": 5,
      "output_position": 2
    }
  ]
}
```

### Contract rules

1. `selection` must already be ordered or orderable by `output_position`
2. `presentation_path` must be explicit
3. `slide_index` must use a single consistent indexing strategy
4. Output path must be precomputed by Python

---

## 8. Slide Indexing Rule

A single indexing convention must be enforced across the system.

### Required convention

* UI displays slides as **1-based**
* stored metadata remains **1-based**
* Node worker converts to the index convention expected by the merge engine

### Design requirement

The conversion boundary must exist only in the worker, not across the whole application.

This avoids inconsistent indexing logic spread across Streamlit and Python services.

---

## 9. Python Merge Service

File: `services/merge_service.py`

Responsibilities:

* persist the merge request
* execute the Node worker
* validate worker outputs
* return structured result to the application

---

## 10. Python Implementation Specification

### 10.1 Merge Service

```python
import json
import subprocess
from pathlib import Path


def save_merge_request(job_path: Path, merge_request: dict) -> Path:
    merge_request_path = job_path / "merge_request.json"
    merge_request_path.write_text(
        json.dumps(merge_request, indent=2),
        encoding="utf-8"
    )
    return merge_request_path


def run_node_merge_worker(job_path: Path, merge_request_path: Path) -> dict:
    worker_dir = Path("workers/node_merge")
    worker_script = worker_dir / "merge_worker.js"

    result = subprocess.run(
        ["node", str(worker_script), str(merge_request_path)],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Node merge worker failed.\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )

    merge_result_path = job_path / "merge_result.json"

    if not merge_result_path.exists():
        raise FileNotFoundError(
            f"Expected merge result file was not generated: {merge_result_path}"
        )

    payload = json.loads(merge_result_path.read_text(encoding="utf-8"))
    return payload


def validate_final_output(merge_result: dict):
    output_path = Path(merge_result["output"])

    if not output_path.exists():
        raise FileNotFoundError(
            f"Expected final PPTX was not generated: {output_path}"
        )

    return output_path
```

---

## 11. Node Worker Responsibilities

The Node worker must:

1. Read the merge request path from CLI arguments
2. Parse the JSON payload
3. Sort the selection by `output_position`
4. Group slides by source presentation if needed by the merge implementation
5. Compose the final PPTX
6. Write a result artifact
7. Exit with non-zero status if composition fails

### Required constraints

* The worker must not contain UI concerns
* The worker must not depend on external services
* The worker must only use local filesystem I/O
* The worker must fail loudly and explicitly

---

## 12. Node Worker Implementation Strategy

The worker must use `pptx-automizer` as the composition engine.

### Expected behavior

* Initialize a new output presentation
* For each selected slide in output order:

  * import the source presentation if not already loaded
  * copy the requested slide
  * append it to the output deck
* write the final `.pptx`

### Important note

The worker should preserve ordering exactly as declared in `output_position`.

No implicit reordering is allowed.

---

## 13. Node Worker Implementation Specification

File: `workers/node_merge/merge_worker.js`

```javascript
const fs = require("fs");
const path = require("path");
const Automizer = require("pptx-automizer").default;

async function main() {
  const requestPath = process.argv[2];

  if (!requestPath) {
    throw new Error("Missing merge request path");
  }

  const request = JSON.parse(fs.readFileSync(requestPath, "utf-8"));
  const jobDir = path.dirname(requestPath);
  const outputPath = request.output;

  const orderedSelection = [...request.selection].sort(
    (a, b) => a.output_position - b.output_position
  );

  const automizer = new Automizer({
    templateDir: ".",
    outputDir: path.dirname(outputPath),
  });

  const presentationCache = new Map();

  for (const item of orderedSelection) {
    if (!fs.existsSync(item.presentation_path)) {
      throw new Error(`Missing source PPTX: ${item.presentation_path}`);
    }

    if (!presentationCache.has(item.presentation_path)) {
      const presName = path.basename(item.presentation_path);
      automizer.loadRoot(item.presentation_path);
      presentationCache.set(item.presentation_path, presName);
    }
  }

  for (const item of orderedSelection) {
    const slideNumber = item.slide_index;
    automizer.addSlide(item.presentation_path, slideNumber);
  }

  await automizer.write(path.basename(outputPath));

  const mergeResultPath = path.join(jobDir, "merge_result.json");
  const resultPayload = {
    status: "success",
    job_id: request.job_id,
    output: outputPath,
    slides_total: orderedSelection.length,
  };

  fs.writeFileSync(
    mergeResultPath,
    JSON.stringify(resultPayload, null, 2),
    "utf-8"
  );

  process.stdout.write(JSON.stringify(resultPayload));
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
```

---

## 14. Package Definition

File: `workers/node_merge/package.json`

```json
{
  "name": "node-merge-worker",
  "version": "1.0.0",
  "private": true,
  "main": "merge_worker.js",
  "dependencies": {
    "pptx-automizer": "^0.7.0"
  }
}
```

### Constraint

The exact library version should be pinned after validation in the PoC environment.

---

## 15. Streamlit Integration

The UI must expose a user action that triggers final composition.

### Required flow

1. Validate that normalized selection exists
2. Build merge request
3. Save merge request
4. Execute Node worker
5. Validate output
6. Store result in session state
7. Enable download control

### Example

```python
import streamlit as st

from services.selection_service import build_merge_request
from services.merge_service import (
    save_merge_request,
    run_node_merge_worker,
    validate_final_output,
)

if "merge_request" in st.session_state and st.session_state.merge_request:
    if st.button("Generate final PPTX"):
        merge_request = st.session_state.merge_request

        merge_request_path = save_merge_request(
            st.session_state.job_path,
            merge_request
        )

        merge_result = run_node_merge_worker(
            st.session_state.job_path,
            merge_request_path
        )

        final_output_path = validate_final_output(merge_result)

        st.session_state.merge_result = merge_result
        st.session_state.final_output_path = str(final_output_path)

        st.success(f"Final PPTX generated: {final_output_path}")
```

---

## 16. Result Artifact

The worker must generate a structured result file.

### Example

```json
{
  "status": "success",
  "job_id": "job_123",
  "output": "tmp/jobs/job_123/outputs/final.pptx",
  "slides_total": 3
}
```

### Requirements

* Must be written to `merge_result.json`
* Must be parseable by Python
* Must include output path
* Must include final slide count

---

## 17. Validation Criteria

This phase is considered complete when:

* A valid merge request can be written to disk
* Python can invoke the Node worker successfully
* The Node worker can read the request and compose the deck
* The final `.pptx` is written under the job output directory
* Python can validate the output file
* Streamlit can reflect merge success

---

## 18. Error Handling Requirements

The implementation must explicitly handle the following cases.

### Missing merge request

If merge request is not available:

* block execution
* show actionable validation message

### Missing source PPTX

If a referenced source file no longer exists:

* fail in the worker
* identify the missing path

### Invalid slide index

If a requested slide index cannot be resolved:

* fail explicitly
* surface which source presentation caused the issue

### Worker execution failure

If subprocess exits with non-zero status:

* capture stdout and stderr
* raise structured error in Python
* display failure in the UI

### Missing output file

If worker reports success but `final.pptx` is missing:

* fail validation in Python
* do not mark job as successful

---

## 19. Constraints and Assumptions

* Composition remains synchronous in this PoC
* The Node worker runs locally from the same application environment
* No remote execution is introduced
* The worker is trusted internal code
* Advanced presentation fidelity is not guaranteed for every source combination
* Theme, master, layout, animation, and embedded object behavior may vary across heterogeneous source presentations

---

## 20. Architectural Decisions

* Python remains the orchestration layer
* Node remains an internal specialized engine
* File-based payload exchange is preferred over HTTP for this PoC
* The merge contract is explicit and stable
* Composition logic is isolated from UI logic
* The output PPTX becomes a first-class job artifact

---

## 21. Exit Criteria

This phase is complete when the system reliably supports:

```text
Selection artifact -> Merge request -> Node worker execution -> Final PPTX generation
```

with the final output written under the job-scoped output directory.

---

## 22. Next Phase

Phase 5 will introduce:

* download handling in Streamlit
* user-facing success and failure states
* job cleanup strategy
* basic operational hardening
* end-to-end validation of the PoC workflow

This phase will consume the generated output artifact without requiring changes to the merge execution model.
