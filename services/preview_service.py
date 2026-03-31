import os
import subprocess
from pathlib import Path

import requests

from services.thumbnail_service import generate_thumbnails

CONVERTER_API_URL = os.getenv("CONVERTER_API_URL")


def _convert_pptx_to_pdf_locally(job_path: Path, pptx_path: Path) -> Path:
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
        raise FileNotFoundError(f"Expected PDF was not generated: {pdf_path}")

    return pdf_path


def _convert_pptx_to_pdf_via_api(job_path: Path, pptx_path: Path) -> Path:
    response = requests.post(
        f"{CONVERTER_API_URL.rstrip('/')}/convert/pptx-to-pdf",
        json={
            "job_path": str(job_path.resolve()),
            "pptx_path": str(pptx_path.resolve()),
        },
        timeout=180,
    )

    if response.status_code >= 400:
        raise RuntimeError(
            f"Conversion API failed for {pptx_path.name}: {response.text}"
        )

    payload = response.json()
    return Path(payload["pdf_path"])


def convert_pptx_to_pdf(job_path: Path, pptx_path: Path) -> Path:
    if CONVERTER_API_URL:
        return _convert_pptx_to_pdf_via_api(job_path, pptx_path)

    return _convert_pptx_to_pdf_locally(job_path, pptx_path)


def generate_previews_for_job(job_path: Path):
    input_dir = job_path / "inputs"
    pptx_files = list(input_dir.glob("*.pptx"))

    previews = []

    for pptx_file in pptx_files:
        pdf_path = convert_pptx_to_pdf(job_path, pptx_file)
        preview_manifest = generate_thumbnails(job_path, pdf_path)
        previews.append(preview_manifest)

    return previews
