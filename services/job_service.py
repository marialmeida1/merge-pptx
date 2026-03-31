import json
import os
import uuid
from pathlib import Path

BASE_DIR = Path(os.getenv("JOB_STORAGE_ROOT", "tmp/jobs"))


def create_job():
    job_id = f"job_{uuid.uuid4().hex[:8]}"
    job_path = BASE_DIR / job_id

    (job_path / "inputs").mkdir(parents=True, exist_ok=True)
    (job_path / "outputs").mkdir(parents=True, exist_ok=True)
    (job_path / "previews").mkdir(parents=True, exist_ok=True)

    metadata = {
        "job_id": job_id,
        "files": [],
        "previews": [],
    }

    (job_path / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    return job_id, job_path
