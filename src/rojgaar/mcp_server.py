"""stdio MCP server exposing ``RojgaarTools`` to Claude Code, Codex and Muse.

Works with the MCP Python SDK 2.x (``MCPServer``) and 1.x (``FastMCP``).
Start it with ``rojgaar mcp`` (or ``uvx rojgaar-scout mcp``).
"""

from __future__ import annotations

from typing import Any

from .config import Paths, get_paths
from .mcp_tools import TOOL_NAMES, RojgaarTools

INSTRUCTIONS = (
    "Rojgaar-Scout tools. Rank today's shortlist with the rubric, draft CVs only from bank claims "
    "(every bullet cites src claim ids), check drafts, save them, then finalize the report. "
    "There is no tool to submit applications, and you must never attempt to."
)


def _server_class() -> Any:
    try:
        from mcp.server.mcpserver import MCPServer  # mcp >= 2

        return MCPServer
    except ImportError:
        from mcp.server.fastmcp import FastMCP  # mcp 1.x

        return FastMCP


def build_server(paths: Paths | None = None, tools: RojgaarTools | None = None) -> Any:
    tools = tools or RojgaarTools(paths or get_paths())
    server = _server_class()("rojgaar", instructions=INSTRUCTIONS)
    for name in TOOL_NAMES:
        method = getattr(tools, name)
        server.tool(name=name, description=(method.__doc__ or name).strip())(method)
    return server


def main() -> None:
    build_server().run("stdio")
