"""Companion script for prompt-builder: extracts generated template and offers save-to-custom."""

import re

import streamlit as st

from prompts import _parse_frontmatter, save_custom_prompt


def _extract_template(result: str) -> str | None:
    """Extract the prompt template from LLM output.

    Tries in order:
    1. Fenced ```markdown code block
    2. First YAML frontmatter block (starts with ---)
    """
    # Try fenced code block first
    match = re.search(r"```markdown\s*\n(.*?)```", result, re.DOTALL)
    if match:
        return match.group(1).strip()
    # Fall back to finding frontmatter start
    idx = result.find("---\n")
    if idx != -1:
        return result[idx:].strip()
    return None


def run(result: str):
    """Parse LLM output for a prompt template and provide save UI."""
    template = _extract_template(result)
    if not template:
        return

    # Read name/description from frontmatter if present
    meta, _ = _parse_frontmatter(template)
    default_name = meta.get("name", "")
    default_desc = meta.get("description", "")

    # Also check for suggested filename in the output
    fname_match = re.search(r"[Ss]uggested filename[:\s]*`?([a-z0-9-]+\.md)`?", result)
    suggested_slug = fname_match.group(1).replace(".md", "") if fname_match else ""

    if not default_name and suggested_slug:
        default_name = suggested_slug.replace("-", " ").title()

    st.subheader("Save as Custom Prompt")

    name = st.text_input("Name", value=default_name, key="pb_save_name")
    auto_id = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") if name else suggested_slug
    prompt_id = st.text_input("ID", value=auto_id, key="pb_save_id")
    if prompt_id and not re.fullmatch(r"[a-z0-9-]+", prompt_id):
        st.warning("ID must contain only lowercase letters, numbers, and hyphens.")
    description = st.text_input("Description", value=default_desc, key="pb_save_desc")
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
