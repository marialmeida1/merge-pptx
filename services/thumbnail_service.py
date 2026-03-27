from pathlib import Path

from pdf2image import convert_from_path


def generate_thumbnails(job_path: Path, pdf_path: Path):
    presentation_preview_dir = job_path / "previews" / pdf_path.stem
    presentation_preview_dir.mkdir(parents=True, exist_ok=True)

    pages = convert_from_path(str(pdf_path), dpi=120)

    slides = []

    for index, page in enumerate(pages, start=1):
        image_path = presentation_preview_dir / f"slide-{index}.png"
        page.save(image_path, "PNG")

        slides.append(
            {
                "slide_index": index,
                "image_path": str(image_path),
            }
        )

    return {
        "presentation_name": pdf_path.stem,
        "pdf_path": str(pdf_path),
        "slides": slides,
    }
