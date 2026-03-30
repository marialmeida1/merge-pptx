import shutil
from pathlib import Path

import streamlit as st


BASE_JOBS_DIR = Path("tmp/jobs").resolve()


def delete_job_directory(job_path: Path):
    resolved_job_path = job_path.resolve()

    if BASE_JOBS_DIR not in resolved_job_path.parents:
        raise ValueError(f"Refusing to delete non-job path: {resolved_job_path}")

    if resolved_job_path.exists():
        shutil.rmtree(resolved_job_path)


def reset_job_session_state():
    keys_to_clear = [
        "job_id",
        "job_path",
        "previews",
        "selected_identities",
        "ordered_identities",
        "normalized_selection",
        "merge_request",
        "merge_result",
        "final_output_path",
        "upload_signature",
    ]

    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
