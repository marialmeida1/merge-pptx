from pathlib import Path

from pdf2image import convert_from_path, pdfinfo_from_path


def _build_slide_image_path(job_path: Path, pdf_path: Path, slide_index: int) -> Path:
    presentation_preview_dir = job_path / "previews" / pdf_path.stem
    presentation_preview_dir.mkdir(parents=True, exist_ok=True)
    return presentation_preview_dir / f"slide-{slide_index}.png"


def generate_thumbnail_for_slide(
    job_path: Path,
    pdf_path: Path,
    slide_index: int,
    dpi: int = 96,
) -> str:
    image_path = _build_slide_image_path(job_path, pdf_path, slide_index)

    if image_path.exists():
        return str(image_path)

    pages = convert_from_path(
        str(pdf_path),
        dpi=dpi,
        first_page=slide_index,
        last_page=slide_index,
    )

    if not pages:
        raise RuntimeError(
            f"Unable to generate thumbnail for slide {slide_index} from {pdf_path.name}"
        )

    pages[0].save(image_path, "PNG")
    return str(image_path)


def generate_thumbnails(job_path: Path, pdf_path: Path):
    pdf_info = pdfinfo_from_path(str(pdf_path))
    total_pages = int(pdf_info["Pages"])

    slides = []

    for index in range(1, total_pages + 1):
        slides.append(
            {
                "slide_index": index,
                "image_path": str(_build_slide_image_path(job_path, pdf_path, index)),
            }
        )

    return {
        "presentation_name": pdf_path.stem,
        "pdf_path": str(pdf_path),
        "slides": slides,
    }
