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
from services.storage_service import (
    list_files,
    save_uploaded_files,
)

st.set_page_config(page_title="Composer PPTX", layout="wide")

st.title("Composer PPTX")

def load_css(css_path: Path):
    css_content = css_path.read_text(encoding="utf-8")
    st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)


load_css(Path(__file__).parent / "styles" / "app.css")


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
        "last_edited_identity": None,
        "top_alert": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def infer_job_state() -> str:
    job_id = st.session_state.get("job_id")
    job_path = st.session_state.get("job_path")

    if not job_id or not job_path:
        return "sem_job"

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
        return "disponivel_para_download"
    if merged:
        return "merge_concluido"
    if merge_ready:
        return "pronto_para_merge"
    if selection_ready:
        return "selecao_pronta"
    if previews_ready:
        return "previews_prontas"
    if files_uploaded:
        return "arquivos_enviados"

    return "criado"


def set_top_alert(message: str, variant: str = "info"):
    st.session_state.top_alert = {
        "message": message,
        "variant": variant,
    }


def render_top_alert():
    alert = st.session_state.get("top_alert")
    if not alert:
        return

    variant = alert.get("variant", "info")
    bg_color = "#1b2434"
    border_color = "#2b79ff"

    if variant == "success":
        bg_color = "#0f2b20"
        border_color = "#18a957"
    elif variant == "error":
        bg_color = "#341a1a"
        border_color = "#e04f4f"

    st.markdown(
        f"""
        <div id="top-alert" style="
            position: fixed;
            top: 72px;
            left: 50%;
            transform: translateX(-50%);
            z-index: 9999;
            background: {bg_color};
            color: #f4f7ff;
            border: 1px solid {border_color};
            border-radius: 10px;
            padding: 10px 16px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.35);
            font-size: 14px;
            min-width: 280px;
            text-align: center;
        ">
            {alert['message']}
        </div>
        <script>
            setTimeout(function() {{
                const el = window.document.getElementById('top-alert');
                if (el) el.remove();
            }}, 3000);
        </script>
        """,
        unsafe_allow_html=True,
    )

    st.session_state.top_alert = None


def clear_pipeline_after_new_inputs():
    st.session_state.previews = None
    st.session_state.selected_identities = []
    st.session_state.ordered_identities = []
    st.session_state.normalized_selection = None
    st.session_state.merge_request = None
    st.session_state.merge_result = None
    st.session_state.final_output_path = None
    st.session_state.last_edited_identity = None


def clear_merge_outputs_only():
    st.session_state.normalized_selection = None
    st.session_state.merge_request = None
    st.session_state.merge_result = None
    st.session_state.final_output_path = None


def sync_ordered_identities(selected_identities: list[str]):
    existing_order = st.session_state.get("ordered_identities", [])

    # Keep current order for still-selected slides and append newly selected ones.
    reconciled_order = [identity for identity in existing_order if identity in selected_identities]
    reconciled_order.extend(
        identity for identity in selected_identities if identity not in reconciled_order
    )

    st.session_state.ordered_identities = reconciled_order


def move_selected_slide(identity: str, direction: str):
    ordered = st.session_state.get("ordered_identities", []).copy()
    if identity not in ordered:
        return

    current_index = ordered.index(identity)
    target_index = current_index - 1 if direction == "left" else current_index + 1

    if target_index < 0 or target_index >= len(ordered):
        return

    ordered[current_index], ordered[target_index] = ordered[target_index], ordered[current_index]
    st.session_state.ordered_identities = ordered


def render_main_download_button():
    final_output_path = st.session_state.get("final_output_path")
    if not final_output_path:
        return

    resolved_output_path = Path(final_output_path)
    if not resolved_output_path.exists():
        return

    st.markdown("### Resultado")
    with open(resolved_output_path, "rb") as final_file:
        st.download_button(
            "Baixar PPTX final",
            final_file,
            file_name=f"final_{st.session_state.job_id}.pptx",
            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            use_container_width=True,
            key="main_download_pptx",
        )


def render_sidebar_controls():
    with st.sidebar:
        st.header("Trabalho")

        if st.button("Criar novo job", use_container_width=True):
            job_id, job_path = create_job()
            st.session_state.job_id = job_id
            st.session_state.job_path = job_path
            st.session_state.upload_signature = None
            clear_pipeline_after_new_inputs()
            set_top_alert(f"Job criado: {job_id}", "success")

        st.markdown(f"**Número do job:** {st.session_state.job_id or 'Nenhum'}")

        if not st.session_state.get("job_id"):
            return

        st.divider()
        st.subheader("Adicionar arquivos")
        uploaded_files = st.file_uploader(
            "Arquivos PPTX",
            type=["pptx"],
            accept_multiple_files=True,
            key="sidebar_uploader",
        )

        if uploaded_files:
            upload_signature = ",".join(
                sorted(f"{item.name}:{item.size}" for item in uploaded_files)
            )
            try:
                if upload_signature != st.session_state.upload_signature:
                    save_uploaded_files(st.session_state.job_path, uploaded_files)

                    st.session_state.upload_signature = upload_signature
                    clear_pipeline_after_new_inputs()
                    st.session_state.previews = generate_previews_for_job(
                        st.session_state.job_path
                    )
                    set_top_alert("Arquivos adicionados e previews gerados.", "success")
            except Exception as error:
                set_top_alert(f"Falha ao gerar previews: {error}", "error")


def render_right_summary_panel():
    selected_count = len(st.session_state.get("selected_identities", []))
    job_state = infer_job_state()
    files_count = 0
    if st.session_state.get("job_path"):
        files_count = len(list_files(st.session_state.job_path))

    if selected_count > 0:
        estimated_size_mb = max(1, round(selected_count * 1.5))
        estimated_time_s = max(2, round(selected_count * 0.8))
        body = (
            f'<div class="summary-row"><span>Estado</span><strong>{job_state}</strong></div>'
            f'<div class="summary-row"><span>Arquivos</span><strong>{files_count}</strong></div>'
            f'<div class="summary-row"><span>Total de slides</span><strong>{selected_count}</strong></div>'
            f'<div class="summary-row"><span>Tamanho estimado</span><strong>{estimated_size_mb}MB</strong></div>'
            f'<div class="summary-row"><span>Tempo de processo</span><strong>~{estimated_time_s}s</strong></div>'
        )
    else:
        body = (
            f'<div class="summary-row"><span>Estado</span><strong>{job_state}</strong></div>'
            f'<div class="summary-row"><span>Arquivos</span><strong>{files_count}</strong></div>'
            '<div class="summary-row"><span>Total de slides</span><strong>0</strong></div>'
            '<div class="summary-row"><span>Tamanho estimado</span><strong>-</strong></div>'
            '<div class="summary-row"><span>Tempo de processo</span><strong>-</strong></div>'
            '<div class="summary-row"><span>Sem dados ainda</span><strong>...</strong></div>'
        )

    job_label = st.session_state.get("job_id") or "Nenhum"

    st.markdown('<div class="summary-title">Resumo</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="summary-row"><span>Trabalho</span><strong>{job_label}</strong></div>{body}',
        unsafe_allow_html=True,
    )

    reset_disabled = not st.session_state.get("job_id")
    if st.button("↺ Reiniciar sessão", key="summary_reset_session", use_container_width=True, disabled=reset_disabled):
        reset_job_session_state()
        set_top_alert("Sessão resetada.", "success")
        st.rerun()

    if st.session_state.get("merge_result"):
        merge_result = st.session_state.merge_result
        status = merge_result.get("status", "-")
        total = merge_result.get("slides_total", "-")
        st.markdown(
            f'<div class="summary-row"><span>Mesclagem</span><strong>{status}</strong></div>'
            f'<div class="summary-row"><span>Slides finais</span><strong>{total}</strong></div>',
            unsafe_allow_html=True,
        )

    if st.session_state.get("final_output_path"):
        final_output_path = Path(st.session_state.final_output_path)
        if final_output_path.exists():
            with open(final_output_path, "rb") as final_file:
                st.download_button(
                    "Baixar PPTX final",
                    final_file,
                    file_name=f"final_{st.session_state.job_id}.pptx",
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    use_container_width=True,
                    key="summary_download_pptx",
                )
        else:
            set_top_alert("O PPTX final era esperado, mas não foi encontrado.", "error")

initialize_session_defaults()
render_top_alert()
render_sidebar_controls()
main_col, right_col = st.columns([4, 1], gap="large")

with right_col:
    st.markdown('<div class="summary-card">', unsafe_allow_html=True)
    render_right_summary_panel()
    st.markdown('</div>', unsafe_allow_html=True)

with main_col:
    if st.session_state.job_id:
        files = list_files(st.session_state.job_path)
        if not files:
            st.caption("Use a lateral para adicionar arquivos a este job.")

    if st.session_state.previews:
        st.subheader("Slides selecionados")

        selected_identities = []
        slide_lookup = {}

        for presentation in st.session_state.previews:
            for slide in presentation["slides"]:
                identity = build_slide_identity(
                    presentation["presentation_name"],
                    slide["slide_index"],
                )
                slide_lookup[identity] = {
                    "presentation_name": presentation["presentation_name"],
                    "slide_index": slide["slide_index"],
                    "image_path": slide["image_path"],
                }

                if st.session_state.get(f"checkbox_{identity}", False):
                    selected_identities.append(identity)

        st.session_state.selected_identities = selected_identities

        if not selected_identities:
            st.caption("Nenhum slide selecionado")
        else:
            sync_ordered_identities(selected_identities)
            ordered_identities = st.session_state.ordered_identities

            st.caption("Use as setas para reordenar os slides selecionados.")

            preview_cols_count = min(4, len(ordered_identities))
            preview_cols = st.columns(preview_cols_count)

            for idx, identity in enumerate(ordered_identities):
                slide_info = slide_lookup.get(identity)
                if slide_info is None:
                    continue

                with preview_cols[idx % preview_cols_count]:
                    left_col, center_col, right_col = st.columns([0.7, 2.6, 0.7])
                    with left_col:
                        if st.button("←", key=f"move_left_{identity}", disabled=idx == 0):
                            move_selected_slide(identity, "left")
                    with center_col:
                        st.caption(f"Posição {idx + 1}")
                    with right_col:
                        if st.button(
                            "→",
                            key=f"move_right_{identity}",
                            disabled=idx == len(ordered_identities) - 1,
                        ):
                            move_selected_slide(identity, "right")

                    st.image(slide_info["image_path"], width=240)
                    st.markdown(f"**Apresentação {slide_info['presentation_name']}**")
                    st.caption(f"Slide {slide_info['slide_index']}")

        st.markdown('<div class="merge-inline">', unsafe_allow_html=True)
        if st.button("Mesclar slides selecionados", use_container_width=True, type="primary"):
            try:
                normalized_selection = normalize_selection(
                    st.session_state.job_path,
                    st.session_state.previews,
                    st.session_state.selected_identities,
                    st.session_state.ordered_identities,
                )

                if not normalized_selection:
                    set_top_alert("Nenhum slide selecionado para merge.", "error")
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

                    set_top_alert(f"Mesclagem concluída: {selection_path}", "success")
            except Exception as error:
                set_top_alert(f"Falha ao mergear slides: {error}", "error")
        st.markdown("</div>", unsafe_allow_html=True)
        render_main_download_button()

        st.subheader("Selecionar slides")

        for presentation in st.session_state.previews:
            st.markdown(f"### {presentation['presentation_name']}")

            cols = st.columns(4)
            for index, slide in enumerate(presentation["slides"]):
                identity = build_slide_identity(
                    presentation["presentation_name"],
                    slide["slide_index"],
                )

                with cols[index % 4]:
                    st.image(
                        slide["image_path"],
                        caption=f"Slide {slide['slide_index']}",
                    )
                    st.checkbox(
                        f"Incluir slide {slide['slide_index']}",
                        key=f"checkbox_{identity}",
                    )

render_top_alert()
