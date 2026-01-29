"""Example companion script. Runs after the LLM responds."""

import streamlit as st


def run(result: str):
    """Display a word count summary below the LLM output."""
    words = len(result.split())
    st.caption(f"Response length: {words} words")
