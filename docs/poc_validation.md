# PoC Validation Report

## 1. PoC Objective

This PoC was created to validate a practical solution for PowerPoint composition with a focus on:

* uploading multiple `.pptx` files
* generating visual slide previews
* selecting and reordering slides
* generating a final consolidated file
* running the system in a containerized environment

Beyond functionality, this PoC also aimed to validate an architecture that is more stable and closer to a production-oriented setup than the original single-container approach.

## 2. Initial Problem

The original scenario concentrated too many responsibilities in a single container:

* Streamlit
* LibreOffice
* Node.js
* preview generation
* final merge

That approach was enough for an initial proof of concept, but it presented clear limitations:

* very large Docker image
* longer build time
* higher chance of runtime instability
* tight coupling between UI and heavy processing
* difficulty evolving toward a more production-like architecture

## 3. Validated Solution

The solution validated in this phase was to split the system into three services:

* `app`: Streamlit and orchestration
* `converter`: FastAPI service with headless LibreOffice for `PPTX -> PDF`
* `merge-worker`: Node.js service with `pptx-automizer` for generating the final PPTX

All three services share a job volume for reading and writing artifacts.

## 4. What Was Successfully Validated

### 4.1 Separation of responsibilities

It was validated that the main Streamlit logic can remain almost unchanged, as long as:

* conversion is accessed via HTTP
* merge is also accessed via HTTP

This preserves the application experience while reducing operational coupling.

### 4.2 LibreOffice isolation

It was validated that LibreOffice can be removed from the main service and isolated in its own service.

Benefits:

* lower complexity in the main container
* lower impact of conversion failures on the UI
* a clearer path to replace the conversion technology in the future

### 4.3 Merge worker isolation

The final merge was also separated from the main app.

Benefits:

* the main service no longer needs to ship Node.js
* merge execution is encapsulated in a specialized service
* the worker can evolve independently from the app

### 4.4 Preservation of the job-based model

The per-job directory model remained valid and useful even after the split into services.

Benefits:

* isolation per execution
* traceability
* simpler debugging
* low implementation cost

### 4.5 Compatibility with a more mature architecture

Even without introducing a queue, database, or asynchronous processing in this phase, the validated architecture already provides a solid foundation for future evolution.

## 5. Accepted Tradeoffs

Every pragmatic PoC makes choices. In this solution, the main tradeoffs were:

### 5.1 Continued use of LibreOffice

Even when isolated, LibreOffice remains a heavy dependency.

Tradeoff:

* it preserves compatibility and simplicity
* but still adds image size, build time, and some instability risk inherent to the tool

Rationale:

* replacing LibreOffice now would significantly increase scope
* for slide preview generation, it remains a practical and well-known solution

### 5.2 Shared volume instead of remote storage

The services share the job directory through a Docker volume instead of using object storage or a database.

Tradeoff:

* simple and fast to operate
* but less flexible for horizontal scaling in distributed environments

Rationale:

* it is sufficient for the current phase
* it keeps the workflow transparent and easy to debug

### 5.3 Synchronous processing

The workflow remains synchronous from the application point of view.

Tradeoff:

* simpler implementation
* more predictable PoC behavior
* but lower scalability for larger processing volumes

Rationale:

* it avoids introducing queues, distributed workers, and additional state too early

### 5.4 Simple internal HTTP communication

Simple internal HTTP communication was adopted between services, without a broker or more advanced orchestration.

Tradeoff:

* easier to understand, implement, and operate
* but less resilient for high-concurrency or retry-heavy scenarios

Rationale:

* it is the smallest solution that clearly solves the current problem

## 6. Known Risks and Limitations

This PoC still has important and intentionally accepted limitations:

### 6.1 Dependence on Docker networking and DNS

During validation, Docker connectivity issues directly impacted image builds.

Implication:

* runtime and build reliability still depend on a healthy local Docker environment

### 6.2 Preview fidelity

The preview is based on `PPTX -> PDF -> PNG`.

Implication:

* there may be differences between the generated preview and native PowerPoint rendering

### 6.3 Merge depends on source file structure

The merge relies on `pptx-automizer`, which is practical but naturally subject to limitations when combining heterogeneous presentations.

Implication:

* layouts, masters, fonts, and complex elements may require additional testing

### 6.4 No queue and no structured retry strategy

Today, if conversion or merge fails, the workflow fails immediately.

Implication:

* there is not yet a robust mechanism for retries, backoff, or controlled reprocessing

## 7. Decisions That Proved Correct

The decisions below proved especially strong for the current phase:

* keeping Streamlit as the main orchestrator
* preserving the functional UI logic
* isolating LibreOffice
* isolating the merge worker
* keeping the job-per-directory model
* using simple APIs between services
* avoiding overengineering at this stage

These choices deliver real improvement without requiring a full product rewrite.

## 8. What This PoC Does Not Try to Solve Yet

To keep scope controlled, this phase did not attempt to solve:

* high concurrency
* asynchronous execution with queues
* relational persistence
* authentication and authorization
* full observability
* autoscaling
* advanced fault tolerance

This is intentional. The PoC was designed to validate the architecture and reduce the main operational problems without turning the project into a complex distributed platform too early.

## 9. Recommended Future Improvements

The next recommended steps, in pragmatic order, are:

### 9.1 Healthchecks and readiness checks

Add explicit checks for:

* `app`
* `converter`
* `merge-worker`

Benefit:

* better operational predictability

### 9.2 Asynchronous processing

Move conversion and merge into asynchronous jobs.

Possible approaches:

* Redis + RQ
* Celery
* managed cloud queue

Benefit:

* better user experience for longer tasks
* decoupling UI responsiveness from processing time

### 9.3 External storage

Replace or complement the local volume with:

* S3
* MinIO
* Azure Blob

Benefit:

* better portability
* better scalability
* lower dependence on the host-local filesystem

### 9.4 Alternative conversion strategy

At the appropriate stage, evaluate:

* CloudConvert
* Microsoft Graph / PowerPoint services
* another specialized backend

Benefit:

* potential reliability and fidelity gains

Tradeoff:

* cost, data governance, and external dependency

### 9.5 Observability

Add:

* structured logs
* `job_id` correlation
* conversion and merge timing metrics
* failure tracing by stage

### 9.6 Integration tests

Create tests that validate:

* upload
* preview generation
* `merge_request` generation
* final merge
* final file existence and readability

## 10. Final Conclusion

This PoC successfully validated that:

* the product is functional from a business point of view
* the architecture can be reorganized without changing the main UI logic
* splitting app, conversion, and merge improves the clarity of the solution
* the new structure is lighter, more stable, and better prepared for future evolution

At the same time, the PoC also made it clear that:

* there are still natural limitations in tools such as LibreOffice
* the system still depends on healthy Docker infrastructure
* the current solution is not yet designed for advanced scale or resilience

In other words, the current solution is a strong transition point between a functional prototype and a lean production-oriented architecture. It addresses real weaknesses in the original design and creates a clear evolution path without introducing unnecessary complexity too early.
