# Budget Planner AI MCP Server

> By [MEOK AI Labs](https://meok.ai) — Comprehensive budget planning with tracking, goals, and analytics

## Installation

```bash
pip install budget-planner-ai-mcp
```

## Usage

```bash
# Run standalone
python server.py

# Or via MCP
mcp install budget-planner-ai-mcp
```

## Tools

### `create_budget`
Create a monthly budget with category allocations.

**Parameters:**
- `month` (str): Budget month
- `income` (float): Total income
- `categories` (dict): Category name to allocation amount mapping

### `add_expense`
Record an expense transaction against a budget category.

**Parameters:**
- `budget_month` (str): Budget month
- `category` (str): Expense category
- `amount` (float): Expense amount
- `description` (str): Description
- `date` (str): Date (YYYY-MM-DD)

### `add_income`
Record income for a budget period.

**Parameters:**
- `budget_month` (str): Budget month
- `source` (str): Income source
- `amount` (float): Income amount

### `get_budget_status`
Get budget status for a month with category-level spending breakdown.

**Parameters:**
- `month` (str): Budget month

### `get_transactions`
List transactions with optional filters by month, category, and date range.

**Parameters:**
- `budget_month` (str): Filter by month
- `category` (str): Filter by category
- `start_date` (str): Start date filter
- `end_date` (str): End date filter
- `limit` (int): Max results (default 50)

### `create_goal`
Create a savings goal with target amount and date.

**Parameters:**
- `name` (str): Goal name
- `target_amount` (float): Target amount
- `target_date` (str): Target date
- `category` (str): Category (default 'Savings')

### `update_goal_progress`
Add contribution to a savings goal.

**Parameters:**
- `goal_id` (str): Goal identifier
- `amount` (float): Contribution amount

### `get_goals`
Get all savings goals with progress percentages.

**Parameters:**
- `status` (str): Filter by status (default 'all')

### `get_analytics`
Get spending analytics by category with totals and averages.

**Parameters:**
- `month` (str): Filter by month
- `category` (str): Filter by category

### `set_budget_alert`
Set spending alert threshold for a category.

**Parameters:**
- `month` (str): Budget month
- `category` (str): Category
- `threshold_percent` (float): Alert threshold percentage

### `get_category_spending`
Get detailed spending by category for a month.

**Parameters:**
- `month` (str): Budget month
- `category` (str): Category

### `transfer_funds`
Transfer budget allocation between categories.

**Parameters:**
- `month` (str): Budget month
- `from_category` (str): Source category
- `to_category` (str): Destination category
- `amount` (float): Transfer amount

### `rollover_unused`
Roll over unused budget to next month.

**Parameters:**
- `source_month` (str): Source month
- `target_month` (str): Target month

## Authentication

Free tier: 15 calls/day. Upgrade at [meok.ai/pricing](https://meok.ai/pricing) for unlimited access.

## License

MIT — MEOK AI Labs
