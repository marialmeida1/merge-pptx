## Slide Selection, Ordering, and Merge Request Construction

## 1. Objective

Extend the application to support **interactive slide selection** and **explicit ordering** of slides drawn from multiple uploaded presentations.

This phase must introduce a deterministic selection model that allows the user to:

* Inspect generated slide previews
* Select slides from different source presentations
* Define the final output order
* Produce a structured merge request payload for downstream composition

This phase intentionally excludes:

* Actual slide merging
* Node.js worker execution
* Final PPTX generation
* Download handling

---

## 2. Scope

For each previewed presentation inside a job, the system must support:

1. Rendering all generated slide previews
2. Allowing the user to include or exclude each slide
3. Capturing selection metadata
4. Allowing the user to define output order across all selected slides
5. Producing a normalized merge request structure to be consumed in Phase 4

---

## 3. Conceptual Model

This phase introduces a new artifact:

```text
Selection = { source presentation, source slide index, output position }
```

The system must treat slide selection as a **job-scoped stateful operation**.

### Input

Preview metadata generated in Phase 2:

```text
job/<id>/previews/<presentation>/slide-<n>.png
```

### Output

A structured selection manifest, for example:

```json
{
  "job_id": "job_123",
  "selection": [
    {
      "selection_id": "sel_001",
      "presentation_name": "deck_a",
      "presentation_path": "tmp/jobs/job_123/inputs/deck_a.pptx",
      "slide_index": 2,
      "output_position": 1
    },
    {
      "selection_id": "sel_002",
      "presentation_name": "deck_c",
      "presentation_path": "tmp/jobs/job_123/inputs/deck_c.pptx",
      "slide_index": 5,
      "output_position": 2
    }
  ]
}
```

This payload becomes the contract between the Streamlit/Python application and the downstream merge engine.

---

## 4. Directory Structure

The job structure must now include selection artifacts:

```text
project/
├─ app.py
├─ services/
│  ├─ job_service.py
│  ├─ storage_service.py
│  ├─ preview_service.py
│  ├─ thumbnail_service.py
│  └─ selection_service.py
├─ tmp/
│  └─ jobs/
│     └─ job_<id>/
│        ├─ inputs/
│        ├─ outputs/
│        ├─ previews/
│        ├─ selection.json
│        └─ metadata.json
└─ requirements.txt
```

### Constraints

* Selection state must remain scoped to the job
* Selection artifacts must be serializable to JSON
* No global selection state may be introduced

---

## 5. Dependencies

No new external dependencies are strictly required in this phase.

### Python dependencies

```text
streamlit
pdf2image
```

### Standard library usage

* `json`
* `uuid`
* `pathlib`

If drag-and-drop ordering is not introduced, native Streamlit components are sufficient.

---

## 6. Component Responsibilities

### 6.1 Streamlit Layer

Responsibilities:

* Render previews with selection controls
* Allow users to include/exclude slides
* Allow users to define final ordering
* Trigger merge request generation
* Persist selection state in session and/or job artifacts

Constraints:

* The UI must not embed selection normalization logic directly
* All merge request construction must be delegated to a service layer

---

### 6.2 Selection Service

File: `services/selection_service.py`

Responsibilities:

* Normalize selected slides into a stable internal structure
* Assign deterministic output positions
* Persist selection to `selection.json`
* Generate merge request payload

Constraints:

* Output ordering must be explicit
* Output must be stable across re-renders
* The service must not depend on UI-specific widget keys

---

## 7. Selection Model

Each selected slide must contain at least:

* `selection_id`
* `presentation_name`
* `presentation_path`
* `slide_index`
* `output_position`

### Example

```json
{
  "selection_id": "sel_abc123",
  "presentation_name": "deck_b",
  "presentation_path": "tmp/jobs/job_123/inputs/deck_b.pptx",
  "slide_index": 4,
  "output_position": 3
}
```

### Rules

1. A slide may be selected independently of other slides from the same presentation
2. Slides from different presentations may coexist in the same output sequence
3. Output order must be explicitly controlled by the user
4. Slide identity must be based on:

   * source presentation
   * slide index

---

## 8. Processing Pipeline

The implementation must follow this sequence:

```text
1. Load preview metadata
2. Render preview cards with selection controls
3. Collect selected slides
4. Normalize the selection into a canonical structure
5. Allow the user to order selected slides
6. Persist selection artifact
7. Produce merge request payload
```

---

## 9. Implementation Specification

### 9.1 Selection Service

File: `services/selection_service.py`

```python
import json
import uuid
from pathlib import Path


def build_slide_identity(presentation_name: str, slide_index: int) -> str:
    return f"{presentation_name}::slide::{slide_index}"


def normalize_selection(job_path: Path, previews: list, selected_identities: list, ordered_identities: list):
    input_dir = job_path / "inputs"
    identity_map = {}

    for presentation in previews:
        presentation_name = presentation["presentation_name"]
        presentation_path = input_dir / f"{presentation_name}.pptx"

        for slide in presentation["slides"]:
            slide_index = slide["slide_index"]
            identity = build_slide_identity(presentation_name, slide_index)

            identity_map[identity] = {
                "presentation_name": presentation_name,
                "presentation_path": str(presentation_path),
                "slide_index": slide_index,
            }

    normalized = []
    output_position = 1

    for identity in ordered_identities:
        if identity not in selected_identities:
            continue

        slide_info = identity_map[identity]

        normalized.append({
            "selection_id": f"sel_{uuid.uuid4().hex[:8]}",
            "presentation_name": slide_info["presentation_name"],
            "presentation_path": slide_info["presentation_path"],
            "slide_index": slide_info["slide_index"],
            "output_position": output_position,
        })

        output_position += 1

    return normalized


def save_selection(job_path: Path, normalized_selection: list):
    selection_path = job_path / "selection.json"

    payload = {
        "job_id": job_path.name,
        "selection": normalized_selection,
    }

    selection_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return selection_path


def build_merge_request(job_path: Path, normalized_selection: list):
    output_path = job_path / "outputs" / "final.pptx"

    return {
        "job_id": job_path.name,
        "output": str(output_path),
        "selection": normalized_selection,
    }
```

---

## 10. UI Design Strategy

The UI should expose two logical sections:

### Section A — Preview Grid

Displays all slide previews grouped by presentation.

Each slide card must include:

* Slide thumbnail
* Slide index
* Selection control

### Section B — Selected Slides

Displays only currently selected slides.

This section must allow:

* Reviewing selected slides
* Defining final order

For the PoC, ordering may be implemented through a numeric position input rather than drag-and-drop.

---

## 11. Streamlit Integration Example

```python
import streamlit as st

from services.selection_service import (
    build_slide_identity,
    normalize_selection,
    save_selection,
    build_merge_request,
)

if "selected_identities" not in st.session_state:
    st.session_state.selected_identities = []

if "ordered_identities" not in st.session_state:
    st.session_state.ordered_identities = []

if st.session_state.previews:
    st.subheader("Select slides")

    all_identities = []

    for presentation in st.session_state.previews:
        st.markdown(f"### {presentation['presentation_name']}")
        cols = st.columns(4)

        for i, slide in enumerate(presentation["slides"]):
            identity = build_slide_identity(
                presentation["presentation_name"],
                slide["slide_index"]
            )
            all_identities.append(identity)

            with cols[i % 4]:
                st.image(slide["image_path"], caption=f"Slide {slide['slide_index']}")
                checked = st.checkbox(
                    f"Include {identity}",
                    key=f"checkbox_{identity}"
                )

                if checked and identity not in st.session_state.selected_identities:
                    st.session_state.selected_identities.append(identity)
                elif not checked and identity in st.session_state.selected_identities:
                    st.session_state.selected_identities.remove(identity)

    selected = st.session_state.selected_identities.copy()

    st.subheader("Order selected slides")

    ordering = []
    for identity in selected:
        position = st.number_input(
            f"Position for {identity}",
            min_value=1,
            max_value=max(1, len(selected)),
            value=selected.index(identity) + 1,
            step=1,
            key=f"position_{identity}"
        )
        ordering.append((identity, position))

    ordered_identities = [
        identity for identity, _ in sorted(ordering, key=lambda item: item[1])
    ]

    st.session_state.ordered_identities = ordered_identities

    if st.button("Build merge request"):
        normalized_selection = normalize_selection(
            st.session_state.job_path,
            st.session_state.previews,
            st.session_state.selected_identities,
            st.session_state.ordered_identities,
        )

        selection_path = save_selection(
            st.session_state.job_path,
            normalized_selection
        )

        merge_request = build_merge_request(
            st.session_state.job_path,
            normalized_selection
        )

        st.session_state.normalized_selection = normalized_selection
        st.session_state.merge_request = merge_request

        st.success(f"Selection saved to {selection_path}")
```

---

## 12. Recommended Improvement for Ordering

The basic numeric ordering input is acceptable for a PoC, but the implementation must enforce uniqueness of positions.

### Minimum rule

No two selected slides may resolve to the same final output position.

### Recommended strategy

After reading the UI positions:

* sort by numeric position
* if duplicates exist, preserve stable insertion order for tie-breaking
* regenerate canonical `output_position` as `1..n`

This ensures the final normalized payload remains valid even if the UI input is imperfect.

---

## 13. Merge Request Shape

The output of this phase must be stable and ready for Phase 4.

### Recommended canonical structure

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

### Rationale

This shape is intentionally verbose to reduce ambiguity in downstream processing.

---

## 14. Validation Criteria

This phase is considered complete when:

* The UI displays previews with selection controls
* Users can select slides from multiple presentations
* Users can define an output order
* The application produces a normalized selection artifact
* The application saves `selection.json` under the job directory
* The application builds a merge request payload ready for Phase 4

---

## 15. Error Handling Requirements

The implementation must explicitly handle the following:

### No previews available

If previews are missing:

* block selection UI
* display actionable message

### No slides selected

If the user attempts to build a merge request with no selection:

* block payload generation
* display validation error

### Invalid ordering

If ordering is incomplete or inconsistent:

* normalize ordering before payload generation
* ensure deterministic final order

### Missing source file

If a preview exists but the corresponding PPTX file is missing:

* fail explicitly during normalization
* identify the missing source

---

## 16. Constraints and Assumptions

* Selection state is job-scoped
* UI state may be stored in Streamlit session state
* No persistent database is introduced
* Ordering is handled synchronously in the UI
* No drag-and-drop dependency is required in this phase
* No actual PPTX manipulation occurs yet

---

## 17. Architectural Decisions

* Preview metadata from Phase 2 is the source of truth for selectable slides
* Selection is serialized to JSON for downstream processing
* Output order is explicit rather than inferred
* Merge request generation is separated from UI logic
* The selection artifact becomes the contract boundary between Phase 3 and Phase 4

---

## 18. Exit Criteria

This phase is complete when the system reliably supports:

```text
Preview display -> Slide selection -> Ordering -> Merge request construction
```

with all selection state and artifacts scoped inside the job directory.

---

## 19. Next Phase

Phase 4 will introduce:

* Node.js worker integration
* execution of the merge engine
* translation of the merge request into the worker input format
* generation of the final `.pptx`

This phase will consume the merge request payload produced here without requiring changes to the selection model.
