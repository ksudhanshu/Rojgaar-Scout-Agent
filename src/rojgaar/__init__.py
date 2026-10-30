"""Rojgaar-Scout: a local-first job search agent for AI coding CLIs.

The deterministic core in this package fetches public job postings, sanitizes,
deduplicates, filters and scores them. The host CLI's model (Claude Code, Codex,
Muse) only ranks a shortlist and drafts CVs through the narrow MCP tools in
``rojgaar.mcp_tools``. The tool never submits applications.
"""

__version__ = "0.1.0"
