---
name: sample-tool
description: A sample tool skill that does I/O, served via MCP.
version: 1.0.0
type: tool
transport: { kind: mcp, server: axis-skills, tool: sample_tool }
io_schema:
  input: { query: string }
  output: { result: string }
tags: [test, shared]
tenants: [maicol]
---

# Sample Tool

A representative `type: tool` skill for tests.
