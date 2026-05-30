# Upstream contract pointer: Model Context Protocol tool-schema spec

Conforms to: Anthropic Model Context Protocol Specification
Bibliography ref: 13, 14, 15, 43

## Source

- Specification site: https://modelcontextprotocol.io
- Specification repository: https://github.com/modelcontextprotocol/specification
- Python SDK: https://github.com/modelcontextprotocol/python-sdk
- FastMCP framework: https://github.com/jlowin/fastmcp
- Maintainer: Anthropic, with community contributions

## Pin

Commit SHA: `d069881d3e1dab5ae76b4bf20806d131d1aa84e5`

The pinned snapshot is the MCP tool-schema spec version the harness/mcp-tool-schemas/ files conform to,
resolved against main HEAD on 2026-05-30.

## How the harness consumes this contract

- The four FastMCP server stubs (`mcp-platform.json`, `mcp-ran.json`, `mcp-hardware.json`, `mcp-ocloud.json`
  in `harness/mcp-tool-schemas/`) declare their tool surface using the MCP tools object shape. Each tool
  has `name`, `description`, `input_schema` (JSON Schema), and an `output_schema_ref` pointing into the
  harness schema set.
- The Agentic Gateway in the architecture diagram (`talk/architecture.mmd`, v3) is the MCP host that loads
  these four servers over stdio.
- The talk's argument that this is "really MCP" (not in-process Python pretending to be MCP) rests on these
  servers being real FastMCP-over-stdio implementations when the runnable demo is built. The stub schemas
  here declare the contract that the runnable layer must honor.

## What we do NOT redistribute

The MCP specification is maintained upstream. We do not vendor the spec text. The harness schemas are
CONSUMERS of the spec (specific tool surface declarations), not a copy of the spec itself.
