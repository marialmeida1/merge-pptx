import json
import uuid
from pathlib import Path


def build_slide_identity(presentation_name: str, slide_index: int) -> str:
    return f"{presentation_name}::slide::{slide_index}"


def normalize_selection(
    job_path: Path,
    previews: list,
    selected_identities: list,
    ordered_identities: list,
):
    input_dir = job_path / "inputs"
    identity_map = {}

    for presentation in previews:
        presentation_name = presentation["presentation_name"]
        presentation_path = input_dir / f"{presentation_name}.pptx"

        if not presentation_path.exists():
            raise FileNotFoundError(
                f"Missing source presentation for preview: {presentation_path}"
            )

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
        if identity not in identity_map:
            continue

        slide_info = identity_map[identity]

        normalized.append(
            {
                "selection_id": f"sel_{uuid.uuid4().hex[:8]}",
                "presentation_name": slide_info["presentation_name"],
                "presentation_path": slide_info["presentation_path"],
                "slide_index": slide_info["slide_index"],
                "output_position": output_position,
            }
        )

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
