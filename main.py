#!/usr/bin/env python3
"""Armis MCP Client - Query Armis security platform via MCP with Ollama LLM."""

import argparse
import asyncio
import sys

import config
from llm import analyze_data, query_with_tools
from mcp_client import ArmisMCPClient
from prompts import build_system_prompt, list_prompts, parse_prompt


async def run_mac_analysis(mac_address: str) -> None:
    """
    Run MAC address risk analysis using deterministic data fetching.

    Flow:
    1. Parse prompt to extract MCP Query
    2. Send query directly to MCP (deterministic)
    3. Send data + analysis prompt to LLM
    """
    print("\n" + "=" * 60)
    print(f"[ANALYSIS] Starting device analysis")
    print(f"[ANALYSIS] MAC Address: {mac_address}")
    print("=" * 60)

    # Parse the prompt template
    parsed = parse_prompt("mac-risk-summarizer", mac_address=mac_address)
    if parsed is None:
        print("[ERROR] mac-risk-summarizer prompt not found", file=sys.stderr)
        sys.exit(1)

    if parsed.mcp_query is None:
        print("[ERROR] No MCP Query section found in prompt template", file=sys.stderr)
        sys.exit(1)

    print(f"\n[PROMPT] Loaded: mac-risk-summarizer")
    print(f"[PROMPT] MCP Query extracted ({len(parsed.mcp_query)} chars)")

    # Connect to MCP and fetch device data
    async with ArmisMCPClient() as client:
        # Step 1: Query MCP directly with the deterministic query
        device_data = await client.query(parsed.mcp_query)

        if not device_data.strip():
            print("[WARNING] MCP returned empty response")
            device_data = "No data returned from Armis for this device."

        # Step 2: Build the analysis prompt with the fetched data
        analysis_prompt = parsed.analysis_prompt.replace("{{device_data}}", device_data)

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


async def interactive_mode() -> None:
    """Run interactive menu mode."""
    prompts = list_prompts()

    print("\n" + "=" * 60)
    print("ARMIS MCP CLIENT - Interactive Mode")
    print("=" * 60)
    print("\nAvailable options:")
    print("-" * 40)
    print("  0. Ask a question (free-form)")
    for i, p in enumerate(prompts, 1):
        print(f"  {i}. {p['name']}: {p['description']}")
    print("-" * 40)

    while True:
        try:
            choice = input("\nSelect option (number) or 'q' to quit: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if choice.lower() == "q":
            break

        try:
            idx = int(choice)
            if idx < 0 or idx > len(prompts):
                print("Invalid selection")
                continue
        except ValueError:
            print("Enter a number or 'q'")
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

        # Handle prompt-specific inputs
        if selected["id"] == "mac-risk-summarizer":
            mac = input("Enter MAC address: ").strip()
            if not mac:
                print("MAC address required")
                continue
            await run_mac_analysis(mac)
        else:
            # Generic handling for other prompts (future)
            print(f"Prompt '{selected['id']}' not yet implemented")


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
        "--query", "-q",
        metavar="QUESTION",
        help="Ask a free-form question",
    )
    parser.add_argument(
        "--interactive", "-i",
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
