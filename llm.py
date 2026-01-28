import json

import ollama

import config
from mcp_client import ArmisMCPClient

MAX_TOOL_ITERATIONS = 5


async def query_with_tools(
    client: ArmisMCPClient,
    system_prompt: str,
    user_prompt: str,
) -> str:
    """
    Query Ollama with MCP tools available.

    Implements a tool-calling loop:
    1. Send prompt to Ollama with tools
    2. If response contains tool_calls, execute via MCP
    3. Append results and repeat
    4. Return final response when no more tool calls
    """
    tools = await client.get_ollama_tools()

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    for iteration in range(MAX_TOOL_ITERATIONS):
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

        for tool_call in tool_calls:
            func = tool_call["function"]
            tool_name = func["name"]
            tool_args = func.get("arguments", {})

            print(f"  [Tool] {tool_name}({json.dumps(tool_args, indent=2)})")

            try:
                result = await client.call_tool(tool_name, tool_args)
            except Exception as e:
                result = f"Error calling tool: {e}"

            messages.append({
                "role": "tool",
                "content": result,
            })

    return messages[-1].get("content", "") if messages else ""
