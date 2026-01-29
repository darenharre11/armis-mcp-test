"""Companion script for prompt-builder: extracts generated template and offers save-to-custom."""

import re

import streamlit as st

from prompts import save_custom_prompt


def run(result: str):
    """Parse LLM output for a prompt template and provide save UI."""
    # Extract fenced markdown code block
    match = re.search(r"```markdown\s*\n(.*?)```", result, re.DOTALL)
    if not match:
        return
    template = match.group(1).strip()

    # Try to extract suggested filename from output
    fname_match = re.search(r"[Ss]uggested filename[:\s]*`?([a-z0-9-]+\.md)`?", result)
    suggested_slug = fname_match.group(1).replace(".md", "") if fname_match else ""

    # Humanize slug for default name
    default_name = suggested_slug.replace("-", " ").title() if suggested_slug else ""

    st.subheader("Save as Custom Prompt")

    name = st.text_input("Name", value=default_name, key="pb_save_name")
    auto_id = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") if name else suggested_slug
    prompt_id = st.text_input("ID", value=auto_id, key="pb_save_id")
    if prompt_id and not re.fullmatch(r"[a-z0-9-]+", prompt_id):
        st.warning("ID must contain only lowercase letters, numbers, and hyphens.")
    description = st.text_input("Description", key="pb_save_desc")
    content = st.text_area("Template", value=template, height=300, key="pb_save_content")

    valid = name.strip() and prompt_id and re.fullmatch(r"[a-z0-9-]+", prompt_id)
    if st.button("Save Prompt", disabled=not valid) and valid:
        save_custom_prompt(
            name.strip(),
            content,
            prompt_id=prompt_id.strip(),
            description=description.strip(),
        )
        st.session_state._show_save_toast = True
        st.session_state._switch_to_prompts = True
        st.rerun()
