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

    def __init__(self):
        self._session = None
        self._read = None
        self._write = None
        self._cm = None
        self._tools = None

    async def __aenter__(self):
        print("\n" + "=" * 60)
        print("[MCP] Connecting to Armis MCP server...")
        print(f"[MCP] URL: {config.ARMIS_MCP_URL}")
        print("=" * 60)

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
        print(f"[MCP] Connected. {len(tools)} tool(s) available:")
        for tool in tools:
            print(f"      - {tool.name}: {tool.description or 'No description'}")
        print("=" * 60 + "\n")
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
        result = await self._session.call_tool(name, arguments)
        if result.content:
            parts = []
            for item in result.content:
                if hasattr(item, "text"):
                    parts.append(item.text)
                else:
                    parts.append(str(item))
            return "\n".join(parts)
        return ""

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

        print("\n" + "-" * 60)
        print("[MCP] Sending query to Armis...")
        print(f"[MCP] Tool: {tool_name}")
        print(f"[MCP] Query:")
        # Print query with indentation for readability
        for line in query_text.strip().split("\n"):
            print(f"      {line}")
        print("-" * 60)

        # Call the tool
        result = await self.call_tool(tool_name, {param_name: query_text})

        print("\n" + "-" * 60)
        print(f"[MCP] Response received ({len(result)} characters)")
        print("[MCP] Response preview:")
        # Show first 500 chars as preview
        preview = result[:500]
        if len(result) > 500:
            preview += f"\n... ({len(result) - 500} more characters)"
        for line in preview.split("\n")[:15]:  # Limit to 15 lines
            print(f"      {line}")
        if preview.count("\n") > 15:
            print(f"      ... (more lines)")
        print("-" * 60 + "\n")

        return result
