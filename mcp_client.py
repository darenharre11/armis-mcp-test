import asyncio

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

import config


def mcp_tool_to_ollama(tool) -> dict:
    """Convert MCP tool schema to Ollama-compatible format."""
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": tool.inputSchema if tool.inputSchema else {"type": "object", "properties": {}},
        },
    }


class ArmisMCPClient:
    """Async context manager for Armis MCP server connection."""

    def __init__(self, on_status=print):
        self._session = None
        self._read = None
        self._write = None
        self._cm = None
        self._tools = None
        self._status = on_status

    async def __aenter__(self):
        self._status("\n" + "=" * 60)
        self._status("[MCP] Connecting to Armis MCP server...")
        self._status(f"[MCP] URL: {config.ARMIS_MCP_URL}")
        self._status("=" * 60)

        self._cm = streamablehttp_client(
            config.ARMIS_MCP_URL,
            headers={"Authorization": f"Bearer {config.ARMIS_API_KEY}"},
        )
        self._read, self._write, _ = await self._cm.__aenter__()
        self._session = ClientSession(self._read, self._write)
        await self._session.__aenter__()
        await self._session.initialize()

        # Verify connection by listing tools
        tools = await self.list_tools()
        self._status(f"[MCP] Connected. {len(tools)} tool(s) available:")
        for tool in tools:
            self._status(f"      - {tool.name}: {tool.description or 'No description'}")
        self._status("=" * 60 + "\n")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            await self._session.__aexit__(exc_type, exc_val, exc_tb)
        if self._cm:
            await self._cm.__aexit__(exc_type, exc_val, exc_tb)

    async def list_tools(self) -> list:
        """List available MCP tools."""
        if self._tools is None:
            result = await self._session.list_tools()
            self._tools = result.tools
        return self._tools

    async def get_ollama_tools(self) -> list[dict]:
        """Get tools in Ollama-compatible format."""
        tools = await self.list_tools()
        return [mcp_tool_to_ollama(t) for t in tools]

    async def call_tool(self, name: str, arguments: dict) -> str:
        """Call an MCP tool and return the result as a string."""
        result = await self._with_heartbeat(
            self._session.call_tool(name, arguments), label=f"MCP:{name}"
        )
        if result.content:
            parts = []
            for item in result.content:
                if hasattr(item, "text"):
                    parts.append(item.text)
                else:
                    parts.append(str(item))
            return "\n".join(parts)
        return ""

    async def _with_heartbeat(self, coro, label="MCP", interval=5):
        """Run a coroutine with periodic heartbeat status messages."""
        async def heartbeat():
            elapsed = 0
            while True:
                await asyncio.sleep(interval)
                elapsed += interval
                self._status(f"  [{label}] Still waiting... ({elapsed}s)")

        task = asyncio.create_task(heartbeat())
        try:
            return await coro
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def query(self, query_text: str) -> str:
        """
        Send a natural language query directly to the MCP server.

        This finds the first available tool and sends the query to it.
        The tool is expected to accept a query/prompt parameter.
        """
        tools = await self.list_tools()
        if not tools:
            raise RuntimeError("No tools available on MCP server")

        # Use the first tool (assumed to be the natural language query tool)
        tool = tools[0]
        tool_name = tool.name

        # Determine the parameter name from the tool's input schema
        input_schema = tool.inputSchema or {}
        properties = input_schema.get("properties", {})

        # Common parameter names for query tools
        param_name = None
        for candidate in ["query", "prompt", "question", "input", "text", "message"]:
            if candidate in properties:
                param_name = candidate
                break

        # If no common name found, use the first property
        if param_name is None and properties:
            param_name = list(properties.keys())[0]

        if param_name is None:
            # Fallback: try with "query" as default
            param_name = "query"

        self._status("\n" + "-" * 60)
        self._status("[MCP] Sending query to Armis...")
        self._status(f"[MCP] Tool: {tool_name}")
        self._status("[MCP] Query:")
        # Print query with indentation for readability
        for line in query_text.strip().split("\n"):
            self._status(f"      {line}")
        self._status("-" * 60)

        # Call the tool
        result = await self.call_tool(tool_name, {param_name: query_text})

        self._status("\n" + "-" * 60)
        self._status(f"[MCP] Response received ({len(result)} characters)")
        self._status("[MCP] Response preview:")
        # Show first 500 chars as preview
        preview = result[:500]
        if len(result) > 500:
            preview += f"\n... ({len(result) - 500} more characters)"
        for line in preview.split("\n")[:15]:  # Limit to 15 lines
            self._status(f"      {line}")
        if preview.count("\n") > 15:
            self._status("      ... (more lines)")
        self._status("-" * 60 + "\n")

        return result
