import subprocess
from pathlib import Path

from services.thumbnail_service import generate_thumbnails


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
        raise FileNotFoundError(f"Expected PDF was not generated: {pdf_path}")

    return pdf_path


def generate_previews_for_job(job_path: Path):
    input_dir = job_path / "inputs"
    pptx_files = list(input_dir.glob("*.pptx"))

    previews = []

    for pptx_file in pptx_files:
        pdf_path = convert_pptx_to_pdf(job_path, pptx_file)
        preview_manifest = generate_thumbnails(job_path, pdf_path)
        previews.append(preview_manifest)

    return previews
