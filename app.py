"""Armis MCP Client - Streamlit web interface."""

import asyncio

import streamlit as st

import config
from main import run_freeform_query, run_prompt_analysis
from prompts import extract_variables, list_prompts, load_visualizer


def run_async(coro):
    """Run async coroutine from sync context, avoiding Streamlit event loop conflicts."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


st.set_page_config(page_title="Armis MCP Client", layout="wide")
st.title("Armis MCP Client")

# Validate config once
try:
    config.validate()
except ValueError as e:
    st.error(f"Configuration error: {e}")
    st.stop()

# Sidebar mode selection
mode = st.sidebar.radio("Mode", ["Prompt Analysis", "Free-form Query"])

if mode == "Prompt Analysis":
    prompts = list_prompts()
    if not prompts:
        st.warning("No prompts found in context/Prompts.md")
        st.stop()

    # Prompt selector
    prompt_labels = {p["id"]: f"{p['name']} - {p['description']}" for p in prompts}
    selected_id = st.selectbox(
        "Select prompt",
        options=[p["id"] for p in prompts],
        format_func=lambda x: prompt_labels[x],
    )

    # Dynamic variable inputs
    variables = extract_variables(selected_id)
    var_values = {}
    for var in variables:
        var_values[var["name"]] = st.text_input(
            var["description"], key=f"var_{var['name']}"
        )

    # Check required variables are filled
    missing = [v["name"] for v in variables if not var_values.get(v["name"])]

    if st.button("Run Analysis", disabled=bool(missing)):
        if missing:
            st.warning(f"Missing required fields: {', '.join(missing)}")
        else:
            status_container = st.status("Running analysis...", expanded=True)
            placeholder = status_container.empty()
            status_lines = []

            def on_status(msg):
                status_lines.append(msg)
                placeholder.text("\n".join(status_lines[-20:]))

            result = run_async(
                run_prompt_analysis(
                    selected_id, on_status=on_status, **var_values
                )
            )
            status_container.update(label="Analysis complete", state="complete")

            st.markdown("---")
            st.markdown(result)

            # Check for companion visualizer
            viz = load_visualizer(selected_id)
            if viz:
                viz(result)

elif mode == "Free-form Query":
    question = st.text_area("Enter your question", height=100)

    if st.button("Ask", disabled=not question.strip()):
        status_container = st.status("Running query...", expanded=True)
        placeholder = status_container.empty()
        status_lines = []

        def on_status(msg):
            status_lines.append(msg)
            placeholder.text("\n".join(status_lines[-20:]))

        result = run_async(
            run_freeform_query(question.strip(), on_status=on_status)
        )
        status_container.update(label="Query complete", state="complete")

        st.markdown("---")
        st.markdown(result)
