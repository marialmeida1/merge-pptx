import os
import subprocess
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="PPTX Converter API", version="1.0.0")
JOB_STORAGE_ROOT = Path(os.getenv("JOB_STORAGE_ROOT", "/data/jobs")).resolve()


class ConvertRequest(BaseModel):
    job_path: str
    pptx_path: str


def resolve_job_path(path_str: str) -> Path:
    resolved = Path(path_str).resolve()
    if JOB_STORAGE_ROOT not in resolved.parents and resolved != JOB_STORAGE_ROOT:
        raise HTTPException(status_code=400, detail=f"Path outside JOB_STORAGE_ROOT: {resolved}")
    return resolved


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/convert/pptx-to-pdf")
def convert_pptx_to_pdf(request: ConvertRequest) -> dict:
    job_path = resolve_job_path(request.job_path)
    pptx_path = resolve_job_path(request.pptx_path)

    if not job_path.exists():
        raise HTTPException(status_code=404, detail=f"Job path not found: {job_path}")

    if not pptx_path.exists():
        raise HTTPException(status_code=404, detail=f"PPTX not found: {pptx_path}")

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
        raise HTTPException(
            status_code=500,
            detail=f"LibreOffice conversion failed for {pptx_path.name}: {result.stderr}",
        )

    pdf_path = previews_dir / f"{pptx_path.stem}.pdf"
    if not pdf_path.exists():
        raise HTTPException(
            status_code=500,
            detail=f"Expected PDF was not generated: {pdf_path}",
        )

    return {
        "status": "success",
        "job_path": str(job_path),
        "pptx_path": str(pptx_path),
        "pdf_path": str(pdf_path),
    }
