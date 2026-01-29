"""Armis MCP Client - Streamlit web interface."""

import asyncio
import re

import streamlit as st

import config
from main import run_custom_analysis, run_freeform_query, run_prompt_analysis
from prompts import (
    build_prompt,
    delete_custom_prompt,
    extract_variables,
    list_custom_prompts,
    list_prompts,
    load_script,
    save_custom_prompt,
)

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
    ("prompt_view", None),
    ("prompt_view_for", None),
    ("history", []),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# Toast for custom prompt save/delete confirmation
if st.session_state.pop("_show_save_toast", False):
    st.toast("Custom prompt saved!")
if st.session_state.pop("_show_delete_toast", False):
    st.toast("Custom prompt deleted.")

# Deferred tab switches (must happen before the radio widget is instantiated)
if st.session_state.pop("_switch_to_results", False):
    st.session_state.active_tab = "Results"
if st.session_state.pop("_switch_to_configure", False):
    st.session_state.active_tab = "Configure"
if st.session_state.pop("_switch_to_prompts", False):
    st.session_state.active_tab = "Prompts"

# Build tab list — Results only when results exist
has_results = st.session_state.result is not None
tab_options = ["Prompts", "Configure", "Results"] if has_results else ["Prompts", "Configure"]

if st.session_state.get("active_tab") not in tab_options:
    st.session_state.active_tab = "Prompts"

st.title("Armis MCP Client")

# Load prompts (built-in + custom)
prompts = list_prompts()
custom_prompts = list_custom_prompts()
all_prompts = prompts + custom_prompts

prompt_map = {p["id"]: p for p in all_prompts}

# Prebuilt catalog includes free-form entry
prebuilt_catalog = prompts + [
    {"id": FREEFORM_ID, "name": "Free-form Query", "description": "Ask any question with tool calling"},
]

tab = st.radio(
    "View",
    tab_options,
    horizontal=True,
    label_visibility="collapsed",
    key="active_tab",
)

def _select_prompt(prompt_id):
    """Handle prompt selection from catalog."""
    st.session_state.selected_prompt = prompt_id
    st.session_state.prompt_view = None
    st.session_state.prompt_view_for = None
    st.session_state._switch_to_configure = True
    st.rerun()


if tab == "Prompts":
    st.subheader("Prebuilt")
    with st.container(border=True):
        col_name, col_desc, col_sel, col_del = st.columns([2, 4, 1, 1])
        col_name.write("**Name**")
        col_desc.write("**Description**")
        col_sel.write("**Select**")
        col_del.write("**Delete**")
        st.divider()
        for i, p in enumerate(prebuilt_catalog):
            col_name, col_desc, col_sel, col_del = st.columns([2, 4, 1, 1])
            col_name.write(p["name"])
            col_desc.write(p["description"])
            if col_sel.button("Select", key=f"sel_{p['id']}"):
                _select_prompt(p["id"])
            col_del.button("Delete", key=f"del_disabled_{p['id']}", disabled=True)
            if i < len(prebuilt_catalog) - 1:
                st.divider()

    st.subheader("Custom")
    if custom_prompts:
        with st.container(border=True):
            col_name, col_desc, col_sel, col_del = st.columns([2, 4, 1, 1])
            col_name.write("**Name**")
            col_desc.write("**Description**")
            col_sel.write("**Select**")
            col_del.write("**Delete**")
            st.divider()
            for i, p in enumerate(custom_prompts):
                col_name, col_desc, col_sel, col_del = st.columns([2, 4, 1, 1])
                col_name.write(p["name"])
                col_desc.write(p["description"])
                if col_sel.button("Select", key=f"sel_{p['id']}"):
                    _select_prompt(p["id"])
                with col_del.popover("Delete"):
                    st.write(f"Delete **{p['name']}**?")
                    if st.button("Confirm", key=f"del_{p['id']}", type="primary"):
                        delete_custom_prompt(p["id"])
                        if st.session_state.get("selected_prompt") == p["id"]:
                            st.session_state.selected_prompt = None
                        st.session_state._show_delete_toast = True
                        st.rerun()
                if i < len(custom_prompts) - 1:
                    st.divider()
    else:
        st.caption("No custom prompts yet. Use Edit > Save as Custom to create one.")

elif tab == "Configure":
    selected_id = st.session_state.get("selected_prompt")
    if not selected_id:
        st.info("Select a prompt from the Prompts tab to get started.")
        st.stop()

    is_freeform = selected_id == FREEFORM_ID

    # Close preview/editor when prompt selection changes
    if st.session_state.prompt_view_for != selected_id:
        st.session_state.prompt_view = None
        st.session_state.prompt_view_for = None

    # Show which prompt is selected
    if is_freeform:
        st.subheader("Free-form Query")
    else:
        st.subheader(prompt_map[selected_id]["name"])

    if is_freeform:
        question = st.text_area("Your question", height=150)

        button_slot = st.empty()
        if button_slot.button("Run", type="primary", disabled=not question.strip()):
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
            st.session_state.history.insert(0, {
                "label": "Free-form Query",
                "result": result,
                "prompt_id": None,
                "log": log,
            })
            st.session_state.history = st.session_state.history[:5]
            st.session_state._switch_to_results = True
            st.rerun()

    else:
        variables = extract_variables(selected_id)
        view = st.session_state.prompt_view

        # Hide variable inputs when editing raw template
        var_values = {}
        if view == "edit":
            st.info(
                "Editing raw prompt. Fill in any `{{variable}}` "
                "placeholders in the **MCP Query** section below."
            )
            missing = []
        else:
            for var in variables:
                var_values[var["name"]] = st.text_input(
                    var["description"], key=f"var_{var['name']}"
                )
            missing = [v["name"] for v in variables if not var_values.get(v["name"])]

        # Button row
        col_edit, col_save, _, col_run = st.columns([1, 1, 2, 1])
        button_slot = col_run.empty()

        if col_edit.button("Edit Prompt" if view != "edit" else "Preview Prompt"):
            if view == "edit":
                st.session_state.prompt_view = "preview"
            else:
                filled = {k: v for k, v in var_values.items() if v}
                content = build_prompt(selected_id, **filled) or ""
                st.session_state.prompt_editor = content
                st.session_state.prompt_view = "edit"
                st.session_state.prompt_view_for = selected_id
            st.rerun()

        if view == "edit":
            with col_save.popover("Save as Custom"):
                save_name = st.text_input("Name", key="save_name")
                auto_id = re.sub(r"[^a-z0-9]+", "-", save_name.lower()).strip("-") if save_name else ""
                save_id = st.text_input("ID", value=auto_id, key="save_id")
                if save_id and not re.fullmatch(r"[a-z0-9-]+", save_id):
                    st.warning("ID must contain only lowercase letters, numbers, and hyphens.")
                save_desc = st.text_input("Description", value="Custom prompt", key="save_desc")
                valid_save = save_name.strip() and save_id and re.fullmatch(r"[a-z0-9-]+", save_id)
                if st.button("Save", disabled=not valid_save) and valid_save:
                    save_custom_prompt(
                        save_name.strip(),
                        st.session_state.prompt_editor,
                        prompt_id=save_id.strip(),
                        description=save_desc.strip(),
                    )
                    st.session_state._show_save_toast = True
                    st.session_state._switch_to_prompts = True
                    st.rerun()

        # Always show prompt — markdown preview by default, text_area when editing
        preview_slot = st.empty()
        with preview_slot:
            if view == "edit":
                st.text_area("Edit prompt", height=400, key="prompt_editor")
            else:
                filled = {k: v for k, v in var_values.items() if v}
                content = build_prompt(selected_id, **filled) or ""
                with st.container(border=True):
                    st.markdown(content)

        # Run — editing bypasses missing-variable check
        can_run = view == "edit" or not missing
        if button_slot.button("Run", type="primary", disabled=not can_run):
            button_slot.button("Running...", type="primary", disabled=True)
            preview_slot.empty()

            status_container = st.status("Running analysis...", expanded=True)
            placeholder = status_container.empty()
            log = []

            def on_status(msg):
                log.append(msg)
                try:
                    placeholder.text("\n".join(log[-20:]))
                except Exception:
                    pass

            if view == "edit":
                result = run_async(
                    run_custom_analysis(
                        st.session_state.prompt_editor, on_status=on_status
                    )
                )
            else:
                result = run_async(
                    run_prompt_analysis(
                        selected_id, on_status=on_status, **var_values
                    )
                )
            status_container.update(label="Complete", state="complete")

            label = prompt_map[selected_id]["name"]
            st.session_state.result = result
            st.session_state.result_prompt_id = selected_id
            st.session_state.result_label = label
            st.session_state.status_log = log
            st.session_state.history.insert(0, {
                "label": label,
                "result": result,
                "prompt_id": selected_id,
                "log": log,
            })
            st.session_state.history = st.session_state.history[:5]
            st.session_state._switch_to_results = True
            st.rerun()

else:
    history = st.session_state.history
    # Pick which run to display
    if len(history) > 1:
        options = [f"{i + 1}. {h['label']}" for i, h in enumerate(history)]
        selected_run = st.selectbox("Run history", options, index=0)
        run_idx = int(selected_run.split(".")[0]) - 1
    else:
        run_idx = 0

    run = history[run_idx] if history else {
        "label": st.session_state.result_label,
        "result": st.session_state.result,
        "prompt_id": st.session_state.result_prompt_id,
        "log": st.session_state.status_log,
    }

    st.subheader(run["label"])
    st.markdown(run["result"])

    prompt_id = run["prompt_id"]
    if prompt_id:
        viz = load_script(prompt_id)
        if viz:
            st.divider()
            viz(run["result"])

    if run["log"]:
        with st.expander("Execution log"):
            st.code("\n".join(run["log"]))

    if st.button("New Analysis"):
        st.session_state.result = None
        st.session_state.result_prompt_id = None
        st.session_state.result_label = None
        st.session_state.status_log = []
        st.session_state._switch_to_prompts = True
        st.rerun()
