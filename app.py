import streamlit as st

from services.job_service import create_job
from services.preview_service import generate_previews_for_job
from services.storage_service import list_files, save_uploaded_files

st.set_page_config(page_title="PPTX Composer", layout="wide")

st.title("PPTX Composer - PoC")

if "job_id" not in st.session_state:
    st.session_state.job_id = None
    st.session_state.job_path = None
    st.session_state.previews = None

if st.button("Create new job"):
    job_id, job_path = create_job()
    st.session_state.job_id = job_id
    st.session_state.job_path = job_path
    st.session_state.previews = None
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
        st.subheader("Uploaded files")
        for f in files:
            st.write(f)

        if st.button("Generate previews"):
            try:
                st.session_state.previews = generate_previews_for_job(
                    st.session_state.job_path
                )
                st.success("Previews generated successfully")
            except Exception as error:
                st.error(f"Preview generation failed: {error}")
    else:
        st.info("No files uploaded")

if st.session_state.previews:
    st.subheader("Slide previews")

    for presentation in st.session_state.previews:
        st.markdown(f"### {presentation['presentation_name']}")

        cols = st.columns(4)
        for index, slide in enumerate(presentation["slides"]):
            with cols[index % 4]:
                st.image(
                    slide["image_path"],
                    caption=f"Slide {slide['slide_index']}",
                )
