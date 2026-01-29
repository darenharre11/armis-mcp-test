import ollama

import config
from mcp_client import ArmisMCPClient

MAX_TOOL_ITERATIONS = 5


def analyze_data(system_prompt: str, user_prompt: str) -> str:
    """
    Query Ollama to analyze data without tool calling.

    Use this when data has already been fetched from MCP and just needs analysis.
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    response = ollama.chat(
        model=config.OLLAMA_MODEL,
        messages=messages,
    )

    return response["message"].get("content", "")


async def query_with_tools(
    client: ArmisMCPClient,
    system_prompt: str,
    user_prompt: str,
    on_status=None,
) -> str:
    """
    Query Ollama with MCP tools available.

    Implements a tool-calling loop:
    1. Send prompt to Ollama with tools
    2. If response contains tool_calls, execute via MCP
    3. Append results and repeat
    4. Return final response when no more tool calls

    Note: For deterministic data fetching, prefer using mcp_client.query()
    directly and then analyze_data() instead of this function.
    """
    if on_status is None:
        on_status = print

    tools = await client.get_ollama_tools()

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    for iteration in range(MAX_TOOL_ITERATIONS):
        on_status(f"  [LLM] Iteration {iteration + 1}/{MAX_TOOL_ITERATIONS}...")

        response = ollama.chat(
            model=config.OLLAMA_MODEL,
            messages=messages,
            tools=tools if tools else None,
        )

        assistant_message = response["message"]
        messages.append(assistant_message)

        tool_calls = assistant_message.get("tool_calls")
        if not tool_calls:
            return assistant_message.get("content", "")

        on_status(f"  [LLM] Executing {len(tool_calls)} tool call(s)...")

        for tool_call in tool_calls:
            func = tool_call["function"]
            tool_name = func["name"]
            tool_args = func.get("arguments", {})

            on_status(f"    - Calling: {tool_name}")

            try:
                result = await client.call_tool(tool_name, tool_args)
                preview = result[:200] + "..." if len(result) > 200 else result
                on_status(f"    - Result: {len(result)} chars")
            except Exception as e:
                result = f"Error calling tool: {e}"
                on_status(f"    - Error: {e}")

            messages.append({
                "role": "tool",
                "content": result,
            })

    on_status("  [LLM] Max iterations reached.")
    return messages[-1].get("content", "") if messages else ""
