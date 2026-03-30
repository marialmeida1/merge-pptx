# PPTX Composer - Workflow and Architecture (External Overview)

## 1. Purpose

This project is a slide composition workflow that allows a user to:

1. Upload multiple PowerPoint files (`.pptx`)
2. Preview all slides visually
3. Select and reorder slides
4. Generate a final merged presentation
5. Download the resulting `.pptx`

The system is designed as a practical Proof of Concept (PoC): clear, modular, and easy to operate.

---

## 2. End-to-End Workflow (Order of Execution)

The flow follows a strict sequence:

1. **Create job**
   - A new job ID is created.
   - The system allocates an isolated job folder.

2. **Ingest files**
   - The user uploads one or more `.pptx` files.
   - Files are stored under the job's `inputs/` folder.

3. **Generate previews**
   - Each uploaded PPTX is converted to PDF using LibreOffice (headless mode).
   - Each PDF page is converted into PNG thumbnails.
   - The UI renders those thumbnails for user interaction.

4. **Select and reorder slides**
   - The user chooses slides to include.
   - Selected slides are reordered via arrow controls.
   - The UI state is normalized into a deterministic selection list.

5. **Build merge request**
   - Python creates a structured JSON payload with:
     - source presentation path
     - source slide index
     - target output position

6. **Run merge worker**
   - Python launches a Node.js worker process.
   - The worker reads the merge request JSON and composes the final PPTX.

7. **Validate output**
   - Python validates that the final output file exists and is readable.

8. **Deliver output**
   - Streamlit exposes a download button for the final presentation.

---

## 3. High-Level Architecture

The architecture is split by responsibility:

1. **Streamlit UI**
   - User interaction layer only.
   - Handles controls, state, and visual feedback.

2. **Python orchestration layer**
   - Coordinates the whole pipeline.
   - Manages jobs, files, preview generation, merge requests, worker execution, and output validation.

3. **LibreOffice preview engine**
   - Converts PPTX to PDF for rendering.
   - Used only for previews.

4. **Node.js merge engine**
   - Performs slide-level composition across multiple PPTX files.
   - Produces the final merged `.pptx`.

5. **Filesystem job storage**
   - Stores all input, intermediate, and final artifacts per job.

---

## 4. Job-Based Model (Why It Matters)

The project uses a **job strategy** to keep execution safe and deterministic.

Benefits:

1. **Isolation**: each run has its own workspace (no file collisions).
2. **Traceability**: input, selection, merge request, and outputs are auditable per run.
3. **Recoverability**: failures affect only one job, not global system state.
4. **Cleanup simplicity**: easy reset/delete at job scope.
5. **Scalability path**: the same model can later support queues and background workers.

---

## 5. Why Docker

Docker is used to guarantee consistent runtime behavior across machines.

Reasons:

1. **Environment consistency**
   - Same OS-level tools and versions for everyone.

2. **Dependency reliability**
   - LibreOffice, Node.js, Python, and related binaries are packaged together.

3. **Reproducibility**
   - Reduces "works on my machine" issues.

4. **Operational simplicity**
   - One containerized setup is easier to run, share, and deploy for demos.

---

## 6. Why Node.js for Merge

Node.js is used specifically for final PPTX composition.

Reasons:

1. **Library capability**
   - `pptx-automizer` provides practical slide copy/merge operations.

2. **Clear boundary of responsibility**
   - Python orchestrates; Node composes.

3. **Low coupling integration**
   - Python calls Node via subprocess and JSON contracts.

4. **Pragmatic architecture**
   - Avoids forcing Python to implement fragile low-level PPTX merge logic.

---

## 7. Why LibreOffice for Preview Generation

LibreOffice is used to render uploaded presentations into preview artifacts.

Reasons:

1. **Headless conversion support**
   - Can run without GUI in server/container contexts.

2. **Broad format compatibility**
   - Handles common Office content types for preview purposes.

3. **Simple pipeline**
   - PPTX -> PDF -> PNG is straightforward and robust for visual inspection.

4. **Separation from final composition**
   - Preview rendering is isolated from merge logic, reducing complexity.

Note: this step can be computationally heavy for very large or complex decks, which is acceptable for the current PoC scope.

---

## 8. Communication Model

Inter-component communication is intentionally simple:

1. **Streamlit <-> Python**: in-process calls
2. **Python <-> LibreOffice**: subprocess command execution
3. **Python <-> Node.js worker**: subprocess + JSON files

No HTTP microservices are required in this PoC.

---

## 9. Current Scope and Practical Limits

This design is intentionally optimized for clarity and fast delivery, not maximum throughput.

Current limitations:

1. Mostly synchronous processing
2. No queue or distributed workers
3. Filesystem-based persistence (no database)
4. Rendering and merge performance depend on deck complexity and machine resources

These constraints are expected for a PoC and can be evolved later.

---

## 10. Summary

This project is a modular PPTX processing pipeline where:

1. Python coordinates the workflow
2. LibreOffice generates visual previews
3. Node.js composes the final presentation
4. Docker guarantees runtime consistency
5. Job isolation keeps processing deterministic and safe

The result is a practical architecture that is simple enough for rapid iteration while still structured enough to scale in future phases.
