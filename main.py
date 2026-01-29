#!/usr/bin/env python3
"""Armis MCP Client - Query Armis security platform via MCP with Ollama LLM."""

import argparse
import asyncio
import sys

import config
from llm import analyze_data, query_with_tools
from mcp_client import ArmisMCPClient
from prompts import build_system_prompt, extract_variables, list_prompts, parse_prompt


async def run_prompt_analysis(prompt_id: str, **variables) -> None:
    """
    Run any prompt-based analysis.

    Flow (with MCP Query):
    1. Parse prompt to extract MCP Query
    2. Send query directly to MCP (deterministic)
    3. Send data + analysis prompt to LLM

    Flow (LLM-only, no MCP Query):
    1. Parse prompt to extract analysis prompt
    2. Send analysis prompt directly to LLM

    Args:
        prompt_id: The prompt ID (filename without .md extension)
        **variables: Variable substitutions for the prompt template
    """
    print("\n" + "=" * 60)
    print(f"[ANALYSIS] Starting analysis with prompt: {prompt_id}")
    for key, value in variables.items():
        print(f"[ANALYSIS] {key}: {value}")
    print("=" * 60)

    # Parse the prompt template
    parsed = parse_prompt(prompt_id, **variables)
    if parsed is None:
        print(f"[ERROR] Prompt '{prompt_id}' not found", file=sys.stderr)
        sys.exit(1)

    print(f"\n[PROMPT] Loaded: {prompt_id}")

    # Check if this is an LLM-only prompt (no MCP query)
    if parsed.mcp_query is None:
        print("[PROMPT] LLM-only mode (no MCP query)")

        # Send analysis prompt directly to LLM
        print("\n" + "=" * 60)
        print("[LLM] Sending prompt to LLM...")
        print(f"[LLM] Model: {config.OLLAMA_MODEL}")
        print(f"[LLM] System prompt: {len(build_system_prompt())} chars")
        print(f"[LLM] Analysis prompt: {len(parsed.analysis_prompt)} chars")
        print("=" * 60)

        system_prompt = build_system_prompt()
        result = analyze_data(system_prompt, parsed.analysis_prompt)

        print("\n" + "=" * 60)
        print("[RESULT] Analysis complete")
        print("=" * 60)
        print("\n" + result)
        return

    print(f"[PROMPT] MCP Query extracted ({len(parsed.mcp_query)} chars)")

    # Connect to MCP and fetch device data
    async with ArmisMCPClient() as client:
        # Step 1: Query MCP directly with the deterministic query
        mcp_data = await client.query(parsed.mcp_query)

        if not mcp_data.strip():
            print("[WARNING] MCP returned empty response")
            mcp_data = "No data returned from Armis."

        # Step 2: Build the analysis prompt with the fetched data
        # Replace common data placeholders
        analysis_prompt = parsed.analysis_prompt
        for placeholder in ["device_data", "data", "mcp_data", "result"]:
            analysis_prompt = analysis_prompt.replace(
                f"{{{{{placeholder}}}}}", mcp_data
            )

        # Step 3: Send to LLM for analysis
        print("\n" + "=" * 60)
        print("[LLM] Sending data to LLM for analysis...")
        print(f"[LLM] Model: {config.OLLAMA_MODEL}")
        print(f"[LLM] System prompt: {len(build_system_prompt())} chars")
        print(f"[LLM] Analysis prompt: {len(analysis_prompt)} chars")
        print("=" * 60)

        system_prompt = build_system_prompt()
        result = analyze_data(system_prompt, analysis_prompt)

        print("\n" + "=" * 60)
        print("[RESULT] Analysis complete")
        print("=" * 60)
        print("\n" + result)


async def run_mac_analysis(mac_address: str) -> None:
    """Run MAC address risk analysis (convenience wrapper)."""
    await run_prompt_analysis("mac-risk-summarizer", mac_address=mac_address)


async def run_freeform_query(question: str) -> None:
    """
    Run a free-form question using LLM-driven tool calling.

    For open-ended questions, the LLM decides what to query.
    """
    print("\n" + "=" * 60)
    print(f"[QUERY] Free-form question mode")
    print(f"[QUERY] Question: {question}")
    print("=" * 60)

    system_prompt = build_system_prompt()

    async with ArmisMCPClient() as client:
        print("\n[LLM] Starting tool-calling loop...")
        result = await query_with_tools(client, system_prompt, question)

        print("\n" + "=" * 60)
        print("[RESULT] Query complete")
        print("=" * 60)
        print("\n" + result)


def display_menu(prompts: list[dict]) -> None:
    """Display the interactive menu options."""
    print("\nAvailable options:")
    print("-" * 40)
    print("  0. Ask a question [Experimental]")
    for i, p in enumerate(prompts, 1):
        print(f"  {i}. {p['name']}: {p['description']}")
    print("-" * 40)


async def interactive_mode() -> None:
    """Run interactive menu mode."""
    prompts = list_prompts()

    print("\n" + "=" * 60)
    print("ARMIS MCP CLIENT - Interactive Mode")
    print("=" * 60)
    display_menu(prompts)

    while True:
        try:
            choice = input(
                "\nSelect option (number), 'l' to list, or 'q' to quit: "
            ).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if choice.lower() == "q":
            break

        if choice.lower() == "l":
            display_menu(prompts)
            continue

        try:
            idx = int(choice)
            if idx < 0 or idx > len(prompts):
                print("Invalid selection")
                continue
        except ValueError:
            print("Enter a number, 'l' to list options, or 'q' to quit")
            continue

        # Free-form question
        if idx == 0:
            question = input("Enter your question: ").strip()
            if not question:
                print("Question required")
                continue
            await run_freeform_query(question)
            continue

        selected = prompts[idx - 1]
        print(f"\nSelected: {selected['name']}")

        # Get variable definitions from the prompt
        variables = extract_variables(selected["id"])

        # Collect values for each variable
        var_values = {}
        for var in variables:
            value = input(f"Enter {var['description']}: ").strip()
            if not value:
                print(f"{var['name']} is required")
                break
            var_values[var["name"]] = value
        else:
            # All variables collected successfully
            await run_prompt_analysis(selected["id"], **var_values)
            continue

        # Variable collection was interrupted (break was hit)
        continue


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Armis MCP Client - Query Armis via MCP with Ollama"
    )
    parser.add_argument(
        "--mac",
        metavar="ADDRESS",
        help="Analyze device by MAC address",
    )
    parser.add_argument(
        "--query",
        "-q",
        metavar="QUESTION",
        help="Ask a free-form question",
    )
    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Run in interactive menu mode",
    )

    args = parser.parse_args()

    try:
        config.validate()
    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.mac:
        asyncio.run(run_mac_analysis(args.mac))
    elif args.query:
        asyncio.run(run_freeform_query(args.query))
    elif args.interactive:
        asyncio.run(interactive_mode())
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
