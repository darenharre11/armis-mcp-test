"""Armis MCP Client - Streamlit web interface."""

import asyncio

import streamlit as st

import config
from main import run_freeform_query, run_prompt_analysis
from prompts import build_prompt, extract_variables, list_prompts, load_visualizer

FREEFORM_ID = "__freeform__"


def run_async(coro):
    """Run async coroutine with proper event loop lifecycle for anyio/MCP."""
    return asyncio.run(coro)


st.set_page_config(page_title="Armis MCP Client", layout="wide")

try:
    config.validate()
except ValueError as e:
    st.error(f"Configuration error: {e}")
    st.stop()

# Session state defaults
for key, default in [
    ("result", None),
    ("result_prompt_id", None),
    ("result_label", None),
    ("status_log", []),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# Auto-switch to Results tab after analysis completes
if st.session_state.pop("_switch_to_results", False):
    st.session_state.active_tab = "Results"

# Only show Results tab when results exist
has_results = st.session_state.result is not None
tab_options = ["Configure", "Results"] if has_results else ["Configure"]

if st.session_state.get("active_tab") not in tab_options:
    st.session_state.active_tab = "Configure"

st.title("Armis MCP Client")

# Load prompts
prompts = list_prompts()

# Build dropdown options: prompts + free-form
options = [p["id"] for p in prompts] + [FREEFORM_ID]
prompt_map = {p["id"]: p for p in prompts}


def format_option(opt):
    if opt == FREEFORM_ID:
        return "Free-form Query"
    return prompt_map[opt]["name"]


tab = st.radio(
    "View",
    tab_options,
    horizontal=True,
    label_visibility="collapsed",
    key="active_tab",
)

if tab == "Configure":
    col_select, col_info = st.columns([3, 1])
    selected_id = col_select.selectbox("Select prompt", options=options, format_func=format_option)
    with col_info.popover("Prompt Catalog"):
        for p in prompts:
            st.markdown(f"**{p['name']}**  \n{p['description']}")
        st.markdown("**Free-form Query**  \nAsk any question with tool calling")
    is_freeform = selected_id == FREEFORM_ID

    if is_freeform:
        st.caption("Ask any question - the LLM decides which tools to call")
        question = st.text_area("Your question", height=150)
        can_run = bool(question.strip())

        button_slot = st.empty()
        if button_slot.button("Run", type="primary", disabled=not can_run):
            button_slot.button("Running...", type="primary", disabled=True)

            status_container = st.status("Running query...", expanded=True)
            placeholder = status_container.empty()
            log = []

            def on_status(msg):
                log.append(msg)
                try:
                    placeholder.text("\n".join(log[-20:]))
                except Exception:
                    pass

            result = run_async(
                run_freeform_query(question.strip(), on_status=on_status)
            )
            status_container.update(label="Complete", state="complete")

            st.session_state.result = result
            st.session_state.result_prompt_id = None
            st.session_state.result_label = "Free-form Query"
            st.session_state.status_log = log
            st.session_state._switch_to_results = True
            st.rerun()

    else:
        st.caption(prompt_map[selected_id]["description"])

        variables = extract_variables(selected_id)
        var_values = {}
        for var in variables:
            var_values[var["name"]] = st.text_input(
                var["description"], key=f"var_{var['name']}"
            )

        missing = [v["name"] for v in variables if not var_values.get(v["name"])]

        col_run, col_preview, _ = st.columns([1, 1, 3])
        button_slot = col_run.empty()
        if col_preview.button("Preview Prompt"):
            preview = build_prompt(selected_id, **var_values)
            if preview:
                with st.expander("Prompt preview", expanded=True):
                    st.code(preview, language="markdown")

        if button_slot.button("Run", type="primary", disabled=bool(missing)):
            button_slot.button("Running...", type="primary", disabled=True)

            status_container = st.status("Running analysis...", expanded=True)
            placeholder = status_container.empty()
            log = []

            def on_status(msg):
                log.append(msg)
                try:
                    placeholder.text("\n".join(log[-20:]))
                except Exception:
                    pass

            result = run_async(
                run_prompt_analysis(selected_id, on_status=on_status, **var_values)
            )
            status_container.update(label="Complete", state="complete")

            st.session_state.result = result
            st.session_state.result_prompt_id = selected_id
            st.session_state.result_label = prompt_map[selected_id]["name"]
            st.session_state.status_log = log
            st.session_state._switch_to_results = True
            st.rerun()

else:
    st.subheader(st.session_state.result_label)
    st.markdown(st.session_state.result)

    prompt_id = st.session_state.result_prompt_id
    if prompt_id:
        viz = load_visualizer(prompt_id)
        if viz:
            st.divider()
            viz(st.session_state.result)

    if st.session_state.status_log:
        with st.expander("Execution log"):
            st.code("\n".join(st.session_state.status_log))

    if st.button("New Analysis"):
        st.session_state.result = None
        st.session_state.result_prompt_id = None
        st.session_state.result_label = None
        st.session_state.status_log = []
        st.session_state.active_tab = "Configure"
        st.rerun()
