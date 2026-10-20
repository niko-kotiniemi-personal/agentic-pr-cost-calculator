# Activity types

Each recorded call carries one label for the kind of work it did, so that the report can split the cost by activity.

**Status:** designed, not built yet.

**Requirements:** R6

## Expected behaviour

The label comes from the first tool the call used:

| The call's first tool | Activity type |
|---|---|
| A file edit or write | code generation |
| A read or a search | file reading |
| A shell command | tooling |
| An MCP tool (`mcp__…`) | MCP |
| Starting a subagent | subagent |
| A tool the classification does not know | other |
| No tool at all | conversation |

The tool's name is read only to choose the label. It is never recorded, because an MCP server's name can name a private service.

## Not covered

- Code review, which cannot be told apart from other work by tool names alone.

## See also

- `usage-capture` in `openspec/`, and design decision 5 of `add-pr-cost-calculator`.
