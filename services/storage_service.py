from pathlib import Path


def save_uploaded_files(job_path: Path, uploaded_files):
    saved_files = []
    input_dir = job_path / "inputs"

    for file in uploaded_files:
        file_path = input_dir / file.name

        with open(file_path, "wb") as f:
            f.write(file.getbuffer())

        saved_files.append(
            {
                "filename": file.name,
                "path": str(file_path),
            }
        )

    return saved_files


def list_files(job_path: Path):
    input_dir = job_path / "inputs"
    return [f.name for f in input_dir.glob("*.pptx")]
