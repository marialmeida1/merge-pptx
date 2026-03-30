import json
import subprocess
from pathlib import Path


def save_merge_request(job_path: Path, merge_request: dict) -> Path:
    resolved_job_path = job_path.resolve()
    merge_request_path = resolved_job_path / "merge_request.json"

    payload = {
        **merge_request,
        "output": str(Path(merge_request["output"]).resolve()),
        "selection": [
            {
                **item,
                "presentation_path": str(Path(item["presentation_path"]).resolve()),
            }
            for item in merge_request["selection"]
        ],
    }

    merge_request_path.write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )
    return merge_request_path


def run_node_merge_worker(job_path: Path, merge_request_path: Path) -> dict:
    project_root = Path(__file__).resolve().parent.parent
    worker_script = project_root / "workers" / "node_merge" / "merge_worker.js"
    resolved_job_path = job_path.resolve()
    resolved_merge_request_path = merge_request_path.resolve()

    result = subprocess.run(
        ["node", str(worker_script), str(resolved_merge_request_path)],
        capture_output=True,
        text=True,
        cwd=str(project_root),
    )

    if result.returncode != 0:
        raise RuntimeError(
            "Node merge worker failed.\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )

    merge_result_path = resolved_job_path / "merge_result.json"

    if not merge_result_path.exists():
        raise FileNotFoundError(
            f"Expected merge result file was not generated: {merge_result_path}"
        )

    return json.loads(merge_result_path.read_text(encoding="utf-8"))


def validate_final_output(merge_result: dict) -> Path:
    output_path = Path(merge_result["output"])

    if not output_path.is_absolute():
        output_path = (Path.cwd() / output_path).resolve()

    if not output_path.exists():
        raise FileNotFoundError(f"Expected final PPTX was not generated: {output_path}")

    if not output_path.is_file():
        raise FileNotFoundError(f"Expected final PPTX path is not a file: {output_path}")

    try:
        with open(output_path, "rb") as file_handle:
            first_byte = file_handle.read(1)
    except OSError as error:
        raise RuntimeError(f"Final PPTX is not readable: {output_path}") from error

    if not first_byte:
        raise RuntimeError(f"Final PPTX is empty: {output_path}")

    return output_path
