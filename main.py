#!/usr/bin/env python3
"""Armis MCP Client - Query Armis security platform via MCP with Ollama LLM."""

import argparse
import asyncio
import sys

import config
from llm import query_with_tools
from mcp_client import ArmisMCPClient
from prompts import build_prompt, build_system_prompt, list_prompts


async def run_mac_analysis(mac_address: str) -> None:
    """Run MAC address risk analysis."""
    print(f"Analyzing device: {mac_address}")

    system_prompt = build_system_prompt()
    user_prompt = build_prompt("mac-risk-summarizer", mac_address=mac_address)

    if user_prompt is None:
        print("Error: mac-risk-summarizer prompt not found", file=sys.stderr)
        sys.exit(1)

    async with ArmisMCPClient() as client:
        result = await query_with_tools(client, system_prompt, user_prompt)
        print("\n" + result)


async def interactive_mode() -> None:
    """Run interactive menu mode."""
    prompts = list_prompts()

    if not prompts:
        print("No prompts available. Add prompts to context/prompts/", file=sys.stderr)
        sys.exit(1)

    print("\nAvailable prompts:")
    print("-" * 60)
    for i, p in enumerate(prompts, 1):
        print(f"  {i}. {p['name']}: {p['description']}")
    print("-" * 60)

    while True:
        try:
            choice = input("\nSelect prompt (number) or 'q' to quit: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if choice.lower() == "q":
            break

        try:
            idx = int(choice) - 1
            if not 0 <= idx < len(prompts):
                print("Invalid selection")
                continue
        except ValueError:
            print("Enter a number or 'q'")
            continue

        selected = prompts[idx]
        print(f"\nSelected: {selected['name']}")

        # Collect variables based on prompt ID
        variables = {}
        if selected["id"] == "mac-risk-summarizer":
            mac = input("Enter MAC address: ").strip()
            if not mac:
                print("MAC address required")
                continue
            variables["mac_address"] = mac

        system_prompt = build_system_prompt()
        user_prompt = build_prompt(selected["id"], **variables)

        if user_prompt is None:
            print(f"Error: Prompt file not found for {selected['id']}")
            continue

        print("\nProcessing...")
        async with ArmisMCPClient() as client:
            result = await query_with_tools(client, system_prompt, user_prompt)
            print("\n" + result)


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
    elif args.interactive:
        asyncio.run(interactive_mode())
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
