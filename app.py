import streamlit as st

from services.job_service import create_job
from services.storage_service import list_files, save_uploaded_files

st.set_page_config(page_title="PPTX Composer", layout="wide")

st.title("PPTX Composer - PoC")

if "job_id" not in st.session_state:
    st.session_state.job_id = None
    st.session_state.job_path = None

if st.button("Create new job"):
    job_id, job_path = create_job()
    st.session_state.job_id = job_id
    st.session_state.job_path = job_path
    st.success(f"Job created: {job_id}")

if st.session_state.job_id:
    uploaded_files = st.file_uploader(
        "Upload PPTX files",
        type=["pptx"],
        accept_multiple_files=True,
    )

    if uploaded_files:
        saved = save_uploaded_files(st.session_state.job_path, uploaded_files)
        st.success(f"{len(saved)} files uploaded successfully")

if st.session_state.job_id:
    files = list_files(st.session_state.job_path)

    if files:
        for f in files:
            st.write(f)
    else:
        st.info("No files uploaded")
