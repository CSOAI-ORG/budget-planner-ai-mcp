<div align="center">

# Budget Planner Ai MCP

**MCP server for budget planner ai mcp operations**

[![PyPI](https://img.shields.io/pypi/v/meok-budget-planner-ai-mcp)](https://pypi.org/project/meok-budget-planner-ai-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![MEOK AI Labs](https://img.shields.io/badge/MEOK_AI_Labs-MCP_Server-purple)](https://meok.ai)

</div>

## Overview

Budget Planner Ai MCP provides AI-powered tools via the Model Context Protocol (MCP).

## Tools

| Tool | Description |
|------|-------------|
| `create_budget` | Create a monthly budget with category allocations |
| `add_expense` | Record an expense transaction |
| `add_income` | Record income for a budget period |
| `get_budget_status` | Get budget status for a month |
| `get_transactions` | List transactions with optional filters |
| `create_goal` | Create a savings goal |
| `update_goal_progress` | Add contribution to a savings goal |
| `get_goals` | Get all savings goals with progress |
| `get_analytics` | Get spending analytics |
| `set_budget_alert` | Set spending alert threshold for a category |
| `get_category_spending` | Get detailed spending by category |
| `transfer_funds` | Transfer between budget categories |
| `rollover_unused` | Rollover unused budget to next month |

## Installation

```bash
pip install meok-budget-planner-ai-mcp
```

## Usage with Claude Desktop

Add to your Claude Desktop MCP config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "budget-planner-ai": {
      "command": "python",
      "args": ["-m", "meok_budget_planner_ai_mcp.server"]
    }
  }
}
```

## Usage with FastMCP

```python
from mcp.server.fastmcp import FastMCP

# This server exposes 13 tool(s) via MCP
# See server.py for full implementation
```

## License

MIT © [MEOK AI Labs](https://meok.ai)
