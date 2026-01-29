#!/usr/bin/env python3
"""Armis MCP Client - Query Armis security platform via MCP with Ollama LLM."""

import argparse
import asyncio
import sys

import config
from llm import analyze_data, query_with_tools
from mcp_client import ArmisMCPClient
from prompts import build_system_prompt, extract_variables, list_prompts, parse_content, parse_prompt


async def run_prompt_analysis(prompt_id: str, on_status=None, **variables) -> str:
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
        on_status: Callback for progress messages (default: print)
        **variables: Variable substitutions for the prompt template

    Returns:
        The LLM analysis result string.
    """
    if on_status is None:
        on_status = print

    on_status("\n" + "=" * 60)
    on_status(f"[ANALYSIS] Starting analysis with prompt: {prompt_id}")
    for key, value in variables.items():
        on_status(f"[ANALYSIS] {key}: {value}")
    on_status("=" * 60)

    # Parse the prompt template
    parsed = parse_prompt(prompt_id, **variables)
    if parsed is None:
        on_status(f"[ERROR] Prompt '{prompt_id}' not found")
        return f"Error: Prompt '{prompt_id}' not found"

    on_status(f"\n[PROMPT] Loaded: {prompt_id}")

    # Check if this is an LLM-only prompt (no MCP query)
    if parsed.mcp_query is None:
        on_status("[PROMPT] LLM-only mode (no MCP query)")

        # Send analysis prompt directly to LLM
        on_status("\n" + "=" * 60)
        on_status("[LLM] Sending prompt to LLM...")
        on_status(f"[LLM] Model: {config.OLLAMA_MODEL}")
        on_status(f"[LLM] System prompt: {len(build_system_prompt())} chars")
        on_status(f"[LLM] Analysis prompt: {len(parsed.analysis_prompt)} chars")
        on_status("=" * 60)

        system_prompt = build_system_prompt()
        result = analyze_data(system_prompt, parsed.analysis_prompt)

        on_status("\n" + "=" * 60)
        on_status("[RESULT] Analysis complete")
        on_status("=" * 60)
        on_status("\n" + result)
        return result

    on_status(f"[PROMPT] MCP Query extracted ({len(parsed.mcp_query)} chars)")

    # Connect to MCP and fetch device data
    async with ArmisMCPClient(on_status=on_status) as client:
        # Step 1: Query MCP directly with the deterministic query
        mcp_data = await client.query(parsed.mcp_query)

        if not mcp_data.strip():
            on_status("[WARNING] MCP returned empty response")
            mcp_data = "No data returned from Armis."

        # Step 2: Build the analysis prompt with the fetched data
        # Replace common data placeholders
        analysis_prompt = parsed.analysis_prompt
        for placeholder in ["device_data", "data", "mcp_data", "result"]:
            analysis_prompt = analysis_prompt.replace(
                f"{{{{{placeholder}}}}}", mcp_data
            )

        # Step 3: Send to LLM for analysis
        on_status("\n" + "=" * 60)
        on_status("[LLM] Sending data to LLM for analysis...")
        on_status(f"[LLM] Model: {config.OLLAMA_MODEL}")
        on_status(f"[LLM] System prompt: {len(build_system_prompt())} chars")
        on_status(f"[LLM] Analysis prompt: {len(analysis_prompt)} chars")
        on_status("=" * 60)

        system_prompt = build_system_prompt()
        result = analyze_data(system_prompt, analysis_prompt)

        on_status("\n" + "=" * 60)
        on_status("[RESULT] Analysis complete")
        on_status("=" * 60)
        on_status("\n" + result)
        return result


async def run_custom_analysis(content: str, on_status=None) -> str:
    """Run analysis from raw prompt content (edited/custom prompt)."""
    if on_status is None:
        on_status = print

    on_status("\n" + "=" * 60)
    on_status("[ANALYSIS] Running custom/edited prompt")
    on_status("=" * 60)

    parsed = parse_content(content)

    if parsed.mcp_query is None:
        on_status("[PROMPT] LLM-only mode (no MCP query)")
        on_status("[LLM] Sending prompt to LLM...")
        system_prompt = build_system_prompt()
        result = analyze_data(system_prompt, parsed.analysis_prompt)
        on_status("[RESULT] Analysis complete")
        return result

    on_status(f"[PROMPT] MCP Query extracted ({len(parsed.mcp_query)} chars)")

    async with ArmisMCPClient(on_status=on_status) as client:
        mcp_data = await client.query(parsed.mcp_query)

        if not mcp_data.strip():
            on_status("[WARNING] MCP returned empty response")
            mcp_data = "No data returned from Armis."

        analysis_prompt = parsed.analysis_prompt
        for placeholder in ["device_data", "data", "mcp_data", "result"]:
            analysis_prompt = analysis_prompt.replace(
                f"{{{{{placeholder}}}}}", mcp_data
            )

        on_status("[LLM] Sending data to LLM for analysis...")
        system_prompt = build_system_prompt()
        result = analyze_data(system_prompt, analysis_prompt)
        on_status("[RESULT] Analysis complete")
        return result


async def run_mac_analysis(mac_address: str, on_status=None) -> str:
    """Run MAC address risk analysis (convenience wrapper)."""
    return await run_prompt_analysis(
        "mac-risk-summarizer", on_status=on_status, mac_address=mac_address
    )


async def run_freeform_query(question: str, on_status=None) -> str:
    """
    Run a free-form question using LLM-driven tool calling.

    For open-ended questions, the LLM decides what to query.

    Returns:
        The LLM result string.
    """
    if on_status is None:
        on_status = print

    on_status("\n" + "=" * 60)
    on_status(f"[QUERY] Free-form question mode")
    on_status(f"[QUERY] Question: {question}")
    on_status("=" * 60)

    system_prompt = build_system_prompt()

    async with ArmisMCPClient(on_status=on_status) as client:
        on_status("\n[LLM] Starting tool-calling loop...")
        result = await query_with_tools(
            client, system_prompt, question, on_status=on_status
        )

        on_status("\n" + "=" * 60)
        on_status("[RESULT] Query complete")
        on_status("=" * 60)
        on_status("\n" + result)
        return result


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
