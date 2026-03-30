import shutil
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


def sync_pptx_from_directory(job_path: Path, source_directory: Path):
    source_directory = source_directory.expanduser().resolve()

    if not source_directory.exists() or not source_directory.is_dir():
        raise FileNotFoundError(f"Directory not found: {source_directory}")

    input_dir = (job_path / "inputs").resolve()
    input_dir.mkdir(parents=True, exist_ok=True)

    source_files = sorted(source_directory.glob("*.pptx"))

    copied_files = []
    skipped_files = []

    for source_file in source_files:
        destination_file = input_dir / source_file.name

        if destination_file.exists():
            src_stat = source_file.stat()
            dest_stat = destination_file.stat()

            same_size = src_stat.st_size == dest_stat.st_size
            same_mtime = int(src_stat.st_mtime) == int(dest_stat.st_mtime)

            if same_size and same_mtime:
                skipped_files.append(source_file.name)
                continue

        shutil.copy2(source_file, destination_file)
        copied_files.append(source_file.name)

    return {
        "source_directory": str(source_directory),
        "found_count": len(source_files),
        "copied_count": len(copied_files),
        "copied_files": copied_files,
        "skipped_count": len(skipped_files),
        "skipped_files": skipped_files,
    }
