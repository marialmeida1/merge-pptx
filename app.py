from pathlib import Path

import streamlit as st

from services.cleanup_service import delete_job_directory, reset_job_session_state
from services.job_service import create_job
from services.merge_service import (
    run_node_merge_worker,
    save_merge_request,
    validate_final_output,
)
from services.preview_service import generate_previews_for_job
from services.selection_service import (
    build_merge_request,
    build_slide_identity,
    normalize_selection,
    save_selection,
)
from services.storage_service import list_files, save_uploaded_files

st.set_page_config(page_title="PPTX Composer", layout="wide")

st.title("PPTX Composer - PoC")


def initialize_session_defaults():
    defaults = {
        "job_id": None,
        "job_path": None,
        "previews": None,
        "selected_identities": [],
        "ordered_identities": [],
        "normalized_selection": None,
        "merge_request": None,
        "merge_result": None,
        "final_output_path": None,
        "upload_signature": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def infer_job_state() -> str:
    job_id = st.session_state.get("job_id")
    job_path = st.session_state.get("job_path")

    if not job_id or not job_path:
        return "no_job"

    resolved_job_path = Path(job_path)
    input_dir = resolved_job_path / "inputs"
    files_uploaded = bool(list(input_dir.glob("*.pptx"))) if input_dir.exists() else False

    previews_ready = bool(st.session_state.get("previews"))
    selection_ready = bool(st.session_state.get("normalized_selection"))
    merge_ready = bool(st.session_state.get("merge_request"))
    merged = bool(st.session_state.get("merge_result"))

    downloadable = False
    final_output_path = st.session_state.get("final_output_path")
    if final_output_path:
        downloadable = Path(final_output_path).exists()

    if downloadable:
        return "downloadable"
    if merged:
        return "merged"
    if merge_ready:
        return "merge_ready"
    if selection_ready:
        return "selection_ready"
    if previews_ready:
        return "previews_ready"
    if files_uploaded:
        return "files_uploaded"

    return "created"


def render_status_banner():
    state = infer_job_state()
    labels = {
        "no_job": "No job exists",
        "created": "Job created, no files uploaded",
        "files_uploaded": "Files uploaded",
        "previews_ready": "Previews generated",
        "selection_ready": "Selection normalized",
        "merge_ready": "Merge request ready",
        "merged": "Merge completed",
        "downloadable": "Download available",
    }
    st.info(f"Workflow state: {labels[state]}")

initialize_session_defaults()
render_status_banner()

if st.button("Create new job"):
    job_id, job_path = create_job()
    st.session_state.job_id = job_id
    st.session_state.job_path = job_path
    st.session_state.previews = None
    st.session_state.selected_identities = []
    st.session_state.ordered_identities = []
    st.session_state.normalized_selection = None
    st.session_state.merge_request = None
    st.session_state.merge_result = None
    st.session_state.final_output_path = None
    st.session_state.upload_signature = None
    st.success(f"Job created: {job_id}")

if st.session_state.job_id:
    uploaded_files = st.file_uploader(
        "Upload PPTX files",
        type=["pptx"],
        accept_multiple_files=True,
    )

    if uploaded_files:
        upload_signature = ",".join(
            sorted(f"{item.name}:{item.size}" for item in uploaded_files)
        )
        try:
            if upload_signature != st.session_state.upload_signature:
                saved = save_uploaded_files(st.session_state.job_path, uploaded_files)
                st.success(f"{len(saved)} files uploaded successfully")

                st.session_state.previews = generate_previews_for_job(
                    st.session_state.job_path
                )
                st.session_state.upload_signature = upload_signature
                st.session_state.normalized_selection = None
                st.session_state.merge_request = None
                st.session_state.merge_result = None
                st.session_state.final_output_path = None
                st.success("Previews generated successfully")
        except Exception as error:
            st.error(f"Preview generation failed: {error}")

if st.session_state.job_id:
    files = list_files(st.session_state.job_path)

    if files:
        st.subheader("Uploaded files")
        for f in files:
            st.write(f)
    else:
        st.info("No files uploaded")

if st.session_state.previews:
    st.subheader("Select slides")

    selected_identities = []
    slide_lookup = {}

    for presentation in st.session_state.previews:
        st.markdown(f"### {presentation['presentation_name']}")

        cols = st.columns(4)
        for index, slide in enumerate(presentation["slides"]):
            identity = build_slide_identity(
                presentation["presentation_name"],
                slide["slide_index"],
            )
            slide_lookup[identity] = {
                "presentation_name": presentation["presentation_name"],
                "slide_index": slide["slide_index"],
                "image_path": slide["image_path"],
            }

            with cols[index % 4]:
                st.image(
                    slide["image_path"],
                    caption=f"Slide {slide['slide_index']}",
                )
                checked = st.checkbox(
                    f"Include slide {slide['slide_index']}",
                    key=f"checkbox_{identity}",
                )
                if checked:
                    selected_identities.append(identity)

    st.session_state.selected_identities = selected_identities

    st.subheader("Order selected slides")

    if not selected_identities:
        st.info("Select at least one slide to define output order")
    else:
        ordering = []
        order_cols = st.columns(3)

        for base_index, identity in enumerate(selected_identities):
            slide_info = slide_lookup.get(identity)

            with order_cols[base_index % 3]:
                if slide_info:
                    st.image(
                        slide_info["image_path"],
                        caption=(
                            f"{slide_info['presentation_name']} - "
                            f"Slide {slide_info['slide_index']}"
                        ),
                    )
                else:
                    st.caption(identity)

                position = st.number_input(
                    "Output position",
                    min_value=1,
                    max_value=max(1, len(selected_identities)),
                    value=base_index + 1,
                    step=1,
                    key=f"position_{identity}",
                )
            ordering.append((identity, position, base_index))

        ordered_identities = [
            identity
            for identity, _, _ in sorted(ordering, key=lambda item: (item[1], item[2]))
        ]
        st.session_state.ordered_identities = ordered_identities

        if st.button("Build merge request"):
            try:
                normalized_selection = normalize_selection(
                    st.session_state.job_path,
                    st.session_state.previews,
                    st.session_state.selected_identities,
                    st.session_state.ordered_identities,
                )

                if not normalized_selection:
                    st.error("No slides selected. Cannot build merge request.")
                else:
                    selection_path = save_selection(
                        st.session_state.job_path,
                        normalized_selection,
                    )
                    merge_request = build_merge_request(
                        st.session_state.job_path,
                        normalized_selection,
                    )

                    st.session_state.normalized_selection = normalized_selection
                    st.session_state.merge_request = merge_request
                    st.session_state.merge_result = None
                    st.session_state.final_output_path = None

                    st.success(f"Selection saved to {selection_path}")
            except Exception as error:
                st.error(f"Failed to build merge request: {error}")

if st.session_state.merge_request:
    st.subheader("Merge request payload")
    st.json(st.session_state.merge_request)

    if st.button("Generate final PPTX"):
        try:
            with st.spinner("Running merge worker..."):
                merge_request_path = save_merge_request(
                    st.session_state.job_path,
                    st.session_state.merge_request,
                )
                merge_result = run_node_merge_worker(
                    st.session_state.job_path,
                    merge_request_path,
                )
                final_output_path = validate_final_output(merge_result)

            st.session_state.merge_result = merge_result
            st.session_state.final_output_path = str(final_output_path)

            st.success(f"Final PPTX generated: {final_output_path}")
        except Exception as error:
            st.error(f"Final PPTX generation failed: {error}")

if st.session_state.get("merge_result"):
    st.subheader("Merge result")
    st.json(st.session_state.merge_result)

if st.session_state.get("final_output_path"):
    final_output_path = Path(st.session_state.final_output_path)
    if final_output_path.exists():
        with open(final_output_path, "rb") as final_file:
            st.download_button(
                "Download final PPTX",
                final_file,
                file_name=f"final_{st.session_state.job_id}.pptx",
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            )
    else:
        st.error("The final PPTX was expected but is missing.")

if st.session_state.get("job_path"):
    st.subheader("Cleanup")
    col_reset, col_delete = st.columns(2)

    with col_reset:
        if st.button("Reset session only"):
            reset_job_session_state()
            st.success("Session reset completed.")
            st.rerun()

    with col_delete:
        if st.button("Delete current job and reset"):
            try:
                delete_job_directory(Path(st.session_state.job_path))
                reset_job_session_state()
                st.success("Current job deleted and session reset.")
                st.rerun()
            except Exception as error:
                st.error(f"Cleanup failed: {error}")

elif st.session_state.job_id and not st.session_state.previews:
    st.info("No previews available yet. Upload PPTX files to generate previews.")
