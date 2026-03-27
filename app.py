import streamlit as st

from services.job_service import create_job
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

if "job_id" not in st.session_state:
    st.session_state.job_id = None
    st.session_state.job_path = None
    st.session_state.previews = None
    st.session_state.selected_identities = []
    st.session_state.ordered_identities = []
    st.session_state.normalized_selection = None
    st.session_state.merge_request = None

if st.button("Create new job"):
    job_id, job_path = create_job()
    st.session_state.job_id = job_id
    st.session_state.job_path = job_path
    st.session_state.previews = None
    st.session_state.selected_identities = []
    st.session_state.ordered_identities = []
    st.session_state.normalized_selection = None
    st.session_state.merge_request = None
    st.success(f"Job created: {job_id}")

if st.session_state.job_id:
    uploaded_files = st.file_uploader(
        "Upload PPTX files",
        type=["pptx"],
        accept_multiple_files=True,
    )

    if uploaded_files:
        try:
            saved = save_uploaded_files(st.session_state.job_path, uploaded_files)
            st.success(f"{len(saved)} files uploaded successfully")

            st.session_state.previews = generate_previews_for_job(
                st.session_state.job_path
            )
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

                    st.success(f"Selection saved to {selection_path}")
            except Exception as error:
                st.error(f"Failed to build merge request: {error}")

if st.session_state.merge_request:
    st.subheader("Merge request payload")
    st.json(st.session_state.merge_request)
elif st.session_state.job_id and not st.session_state.previews:
    st.info("No previews available yet. Upload PPTX files to generate previews.")
