import json
from contextlib import asynccontextmanager

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
        self._cm = streamablehttp_client(
            config.ARMIS_MCP_URL,
            headers={"Authorization": f"Bearer {config.ARMIS_API_KEY}"},
        )
        self._read, self._write, _ = await self._cm.__aenter__()
        self._session = ClientSession(self._read, self._write)
        await self._session.__aenter__()
        await self._session.initialize()
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
