# Architecture Overview Document

## 1. Overview

The PPTX Composer is a document processing system designed to:

* Ingest multiple `.pptx` files
* Render slide previews
* Allow user-driven slide selection and ordering
* Generate a new `.pptx` composed from selected slides

The system follows a **pipeline-based architecture**, where each stage transforms or enriches the input data until a final output is produced.

---

## 2. High-Level Architecture

```text
[ Streamlit UI ]
        |
        v
[ Python Orchestrator ]
   |         |         |
   |         |         +--> [ Node Worker (pptx-automizer) ]
   |         |
   |         +--> [ Preview Engine (LibreOffice) ]
   |
   +--> [ Job Storage (filesystem) ]
```

---

## 3. Core Components

### 3.1 User Interface (Streamlit)

The Streamlit application provides the user-facing layer.

Responsibilities:

* Upload multiple `.pptx` files
* Display slide previews
* Allow slide selection and ordering
* Trigger final composition
* Provide download of the generated presentation

This layer contains no heavy processing logic and acts purely as an interaction interface.

---

### 3.2 Python Orchestrator

The Python layer is the central coordination component.

Responsibilities:

* Manage job lifecycle and isolation
* Handle file storage and organization
* Execute preview generation
* Build selection and merge request artifacts
* Invoke the Node.js worker
* Validate outputs and expose results to the UI

The orchestrator does not perform complex PPTX manipulation directly; it delegates specialized tasks to external components.

---

### 3.3 Job Storage (Filesystem)

All processing is scoped within a **job-specific directory**.

```text
job/
├─ inputs/
├─ previews/
├─ outputs/
├─ selection.json
└─ merge_request.json
```

Responsibilities:

* Store uploaded files
* Store intermediate artifacts (PDFs, images)
* Store selection and merge metadata
* Store final output

This design ensures **job isolation**, preventing conflicts and enabling deterministic processing.

---

### 3.4 Preview Engine (LibreOffice)

The preview engine is responsible for rendering slides.

Processing pipeline:

```text
PPTX -> PDF -> PNG images
```

Responsibilities:

* Convert `.pptx` files to PDF using headless execution
* Enable downstream conversion of PDF pages into images
* Provide visual representations of slides for user interaction

This component is used exclusively for preview purposes and is not involved in final composition.

---

### 3.5 Composition Engine (Node.js + pptx-automizer)

The Node.js worker performs the actual slide composition.

Responsibilities:

* Load source `.pptx` files
* Copy selected slides
* Preserve slide structure as much as possible
* Generate the final `.pptx` output

The Python layer communicates with this worker via a **file-based JSON contract**, ensuring loose coupling.

---

## 4. System Workflow

The system operates as a sequential pipeline:

```text
1. Upload PPTX files
2. Generate slide previews
3. Select slides
4. Define output order
5. Build merge request
6. Execute Node worker
7. Generate final PPTX
8. Download result
```

Each step produces artifacts that are consumed by the next stage.

---

## 5. Interaction Model

### Python ↔ LibreOffice

* Python invokes LibreOffice via subprocess
* Input: `.pptx`
* Output: `.pdf`

### Python ↔ Node Worker

* Communication via JSON files (`merge_request.json`, `merge_result.json`)
* Execution via subprocess
* No HTTP or network communication

### Streamlit ↔ Python

* Direct in-process interaction
* State managed via session state

---

## 6. Key Architectural Decisions

### Separation of Responsibilities

Each component is specialized:

| Component   | Responsibility    |
| ----------- | ----------------- |
| Python      | Orchestration     |
| LibreOffice | Rendering         |
| Node.js     | PPTX manipulation |
| Streamlit   | User interaction  |

---

### Minimal Node Usage

Node.js is used only for slide composition, minimizing cross-language complexity.

---

### File-Based Communication

Inter-process communication uses filesystem-based JSON contracts instead of HTTP APIs to reduce infrastructure complexity.

---

### Job Isolation

Each job operates in a separate directory, ensuring:

* No file collisions
* No shared state
* Safe concurrent usage

---

### Synchronous Pipeline

All processing is synchronous to simplify execution and debugging in the PoC.

---

## 7. Limitations

This architecture is intentionally simplified for a proof of concept.

Known limitations:

* No asynchronous processing or job queue
* No persistent database
* Limited scalability
* Potential rendering differences between LibreOffice and PowerPoint
* Possible layout inconsistencies when merging heterogeneous presentations

---

## 8. Conclusion

The system is designed as a **modular document processing pipeline** where:

* Python orchestrates execution
* LibreOffice handles rendering
* Node.js handles composition
* Streamlit provides the user interface
* Filesystem-based job isolation ensures safe and deterministic processing

This architecture prioritizes **simplicity, clarity, and speed of implementation**, making it well-suited for a proof of concept while remaining extensible for future evolution.
