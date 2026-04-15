#!/usr/bin/env python3
"""MEOK AI Labs — budget-planner-ai-mcp MCP Server. Comprehensive budget planning with tracking, goals, and analytics."""

import asyncio
import json
from datetime import datetime, timedelta, timezone
from typing import Any
import uuid
from collections import defaultdict

from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
from mcp.types import Resource, Tool, TextContent
import mcp.types as types
import sys, os
sys.path.insert(0, os.path.expanduser("~/clawd/meok-labs-engine/shared"))
from auth_middleware import check_access
from collections import defaultdict
import json

FREE_DAILY_LIMIT = 15
_usage = defaultdict(list)
def _rl(c="anon"):
    now = datetime.now(timezone.utc)
    _usage[c] = [t for t in _usage[c] if (now-t).total_seconds() < 86400]
    if len(_usage[c]) >= FREE_DAILY_LIMIT: return json.dumps({"error": f"Limit {FREE_DAILY_LIMIT}/day"})
    _usage[c].append(now); return None

_store = {
    "budgets": {},
    "transactions": [],
    "goals": [],
    "categories": [
        "Housing",
        "Transportation",
        "Food",
        "Utilities",
        "Insurance",
        "Healthcare",
        "Entertainment",
        "Personal",
        "Education",
        "Savings",
        "Debt",
        "Gifts",
        "Subscriptions",
        "Misc",
    ],
}

server = Server("budget-planner-ai")


def create_id():
    return str(uuid.uuid4())[:8]


@server.list_resources()
async def handle_list_resources() -> list[Resource]:
    return [
        Resource(
            uri="budget://dashboard",
            name="Budget Dashboard",
            description="Overview of all budgets",
            mimeType="application/json",
        ),
        Resource(
            uri="budget://transactions",
            name="Transactions",
            description="All recorded transactions",
            mimeType="application/json",
        ),
        Resource(
            uri="budget://goals",
            name="Savings Goals",
            description="Active savings goals",
            mimeType="application/json",
        ),
    ]


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    return [
        Tool(
            name="create_budget",
            description="Create a monthly budget with category allocations",
            inputSchema={
                "type": "object",
                "properties": {
                    "month": {"type": "string", "description": "Month (YYYY-MM)"},
                    "income": {"type": "number"},
                    "categories": {"type": "object", "description": "Category: amount"},
                },
                "required": ["month", "income", "categories"],
            },
        ),
        Tool(
            name="add_expense",
            description="Record an expense transaction",
            inputSchema={
                "type": "object",
                "properties": {
                    "budget_month": {"type": "string"},
                    "category": {"type": "string"},
                    "amount": {"type": "number"},
                    "description": {"type": "string"},
                    "date": {"type": "string"},
                },
                "required": ["budget_month", "category", "amount"],
            },
        ),
        Tool(
            name="add_income",
            description="Record income for a budget period",
            inputSchema={
                "type": "object",
                "properties": {
                    "budget_month": {"type": "string"},
                    "source": {"type": "string"},
                    "amount": {"type": "number"},
                    "date": {"type": "string"},
                },
                "required": ["budget_month", "source", "amount"],
            },
        ),
        Tool(
            name="get_budget_status",
            description="Get budget status for a month",
            inputSchema={
                "type": "object",
                "properties": {"month": {"type": "string"}},
                "required": ["month"],
            },
        ),
        Tool(
            name="get_transactions",
            description="List transactions with optional filters",
            inputSchema={
                "type": "object",
                "properties": {
                    "budget_month": {"type": "string"},
                    "category": {"type": "string"},
                    "start_date": {"type": "string"},
                    "end_date": {"type": "string"},
                    "limit": {"type": "number"},
                },
            },
        ),
        Tool(
            name="create_goal",
            description="Create a savings goal",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "target_amount": {"type": "number"},
                    "target_date": {"type": "string"},
                    "category": {"type": "string"},
                },
                "required": ["name", "target_amount", "target_date"],
            },
        ),
        Tool(
            name="update_goal_progress",
            description="Add contribution to a savings goal",
            inputSchema={
                "type": "object",
                "properties": {
                    "goal_id": {"type": "string"},
                    "amount": {"type": "number"},
                },
                "required": ["goal_id", "amount"],
            },
        ),
        Tool(
            name="get_goals",
            description="Get all savings goals with progress",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["active", "completed", "all"]}
                },
            },
        ),
        Tool(
            name="get_analytics",
            description="Get spending analytics",
            inputSchema={
                "type": "object",
                "properties": {
                    "month": {"type": "string"},
                    "category": {"type": "string"},
                },
            },
        ),
        Tool(
            name="set_budget_alert",
            description="Set spending alert threshold for a category",
            inputSchema={
                "type": "object",
                "properties": {
                    "month": {"type": "string"},
                    "category": {"type": "string"},
                    "threshold_percent": {"type": "number"},
                },
                "required": ["month", "category", "threshold_percent"],
            },
        ),
        Tool(
            name="get_category_spending",
            description="Get detailed spending by category",
            inputSchema={
                "type": "object",
                "properties": {
                    "month": {"type": "string"},
                    "category": {"type": "string"},
                },
            },
        ),
        Tool(
            name="transfer_funds",
            description="Transfer between budget categories",
            inputSchema={
                "type": "object",
                "properties": {
                    "month": {"type": "string"},
                    "from_category": {"type": "string"},
                    "to_category": {"type": "string"},
                    "amount": {"type": "number"},
                },
                "required": ["month", "from_category", "to_category", "amount"],
            },
        ),
        Tool(
            name="rollover_unused",
            description="Rollover unused budget to next month",
            inputSchema={
                "type": "object",
                "properties": {
                    "source_month": {"type": "string"},
                    "target_month": {"type": "string"},
                },
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: Any | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    args = arguments or {}
    api_key = args.get("api_key", "")
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return [TextContent(type="text", text=json.dumps({"error": msg, "upgrade_url": "https://meok.ai/pricing"}))]
    if err := _rl(): return [TextContent(type="text", text=err)]

    if name == "create_budget":
        month = args["month"]
        income = args["income"]
        categories = args["categories"]

        total_allocated = sum(categories.values())
        remaining = round(income - total_allocated, 2)

        budget = {
            "id": create_id(),
            "month": month,
            "income": income,
            "allocated": total_allocated,
            "remaining": remaining,
            "categories": categories,
            "spent": {cat: 0 for cat in categories},
            "alerts": {},
            "created_at": datetime.now().isoformat(),
        }
        _store["budgets"][month] = budget

        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "budget_created": True,
                        "month": month,
                        "income": income,
                        "allocated": total_allocated,
                        "remaining": remaining,
                        "categories": list(categories.keys()),
                        "tip": "Track every expense to stay on budget!",
                    },
                    indent=2,
                ),
            )
        ]

    elif name == "add_expense":
        month = args["budget_month"]
        category = args["category"]
        amount = args["amount"]
        description = args.get("description", "")
        date = args.get("date", datetime.now().strftime("%Y-%m-%d"))

        if month not in _store["budgets"]:
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {"error": f"Budget for {month} not found. Create it first."},
                        indent=2,
                    ),
                )
            ]

        budget = _store["budgets"][month]

        if category not in budget["categories"]:
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "error": f"Category '{category}' not in budget. Use: {list(budget['categories'].keys())}"
                        },
                        indent=2,
                    ),
                )
            ]

        transaction = {
            "id": create_id(),
            "type": "expense",
            "month": month,
            "category": category,
            "amount": amount,
            "description": description,
            "date": date,
        }
        _store["transactions"].append(transaction)

        budget["spent"][category] = budget["spent"].get(category, 0) + amount

        remaining_budget = budget["categories"][category] - budget["spent"][category]
        alert_threshold = budget["alerts"].get(category)

        result = {
            "expense_recorded": True,
            "transaction_id": transaction["id"],
            "category": category,
            "amount": amount,
            "remaining_in_category": remaining_budget,
        }

        if alert_threshold and remaining_budget < (
            budget["categories"][category] * (100 - alert_threshold) / 100
        ):
            result["alert"] = (
                f"WARNING: You've used {alert_threshold}% of your {category} budget!"
            )

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "add_income":
        month = args["budget_month"]
        source = args["source"]
        amount = args["amount"]
        date = args.get("date", datetime.now().strftime("%Y-%m-%d"))

        if month not in _store["budgets"]:
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {"error": f"Budget for {month} not found"}, indent=2
                    ),
                )
            ]

        budget = _store["budgets"][month]
        budget["income"] += amount
        budget["remaining"] += amount

        transaction = {
            "id": create_id(),
            "type": "income",
            "month": month,
            "source": source,
            "amount": amount,
            "date": date,
        }
        _store["transactions"].append(transaction)

        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "income_recorded": True,
                        "transaction_id": transaction["id"],
                        "new_total_income": budget["income"],
                        "new_remaining": budget["remaining"],
                    },
                    indent=2,
                ),
            )
        ]

    elif name == "get_budget_status":
        month = args["month"]
        if month not in _store["budgets"]:
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {"error": f"Budget for {month} not found"}, indent=2
                    ),
                )
            ]

        budget = _store["budgets"][month]
        total_spent = sum(budget["spent"].values())

        category_status = {}
        for cat, allocated in budget["categories"].items():
            spent = budget["spent"].get(cat, 0)
            pct = round((spent / allocated) * 100, 1) if allocated > 0 else 0
            category_status[cat] = {
                "allocated": allocated,
                "spent": spent,
                "remaining": round(allocated - spent, 2),
                "percent_used": pct,
                "status": "ok" if pct < 80 else "warning" if pct < 100 else "over",
            }

        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "month": month,
                        "income": budget["income"],
                        "total_allocated": budget["allocated"],
                        "total_spent": total_spent,
                        "total_remaining": budget["remaining"],
                        "categories": category_status,
                    },
                    indent=2,
                ),
            )
        ]

    elif name == "get_transactions":
        month = args.get("budget_month")
        category = args.get("category")
        start = args.get("start_date")
        end = args.get("end_date")
        limit = args.get("limit", 50)

        txns = _store["transactions"][-limit:]

        if month:
            txns = [t for t in txns if t.get("month") == month]
        if category:
            txns = [t for t in txns if t.get("category") == category]
        if start:
            txns = [t for t in txns if t.get("date", "") >= start]
        if end:
            txns = [t for t in txns if t.get("date", "") <= end]

        return [
            TextContent(type="text", text=json.dumps({"transactions": txns}, indent=2))
        ]

    elif name == "create_goal":
        goal = {
            "id": create_id(),
            "name": args["name"],
            "target_amount": args["target_amount"],
            "target_date": args["target_date"],
            "category": args.get("category", "Savings"),
            "current_amount": 0,
            "status": "active",
            "created_at": datetime.now().isoformat(),
        }
        _store["goals"].append(goal)

        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "goal_created": True,
                        "goal_id": goal["id"],
                        "name": goal["name"],
                        "target": goal["target_amount"],
                        "target_date": goal["target_date"],
                    },
                    indent=2,
                ),
            )
        ]

    elif name == "update_goal_progress":
        goal_id = args["goal_id"]
        amount = args["amount"]

        for goal in _store["goals"]:
            if goal["id"] == goal_id:
                goal["current_amount"] += amount
                if goal["current_amount"] >= goal["target_amount"]:
                    goal["status"] = "completed"

                return [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "updated": True,
                                "goal_id": goal_id,
                                "current": goal["current_amount"],
                                "target": goal["target_amount"],
                                "progress_percent": round(
                                    (goal["current_amount"] / goal["target_amount"])
                                    * 100,
                                    1,
                                ),
                                "completed": goal["status"] == "completed",
                            },
                            indent=2,
                        ),
                    )
                ]

        return [
            TextContent(
                type="text", text=json.dumps({"error": "Goal not found"}, indent=2)
            )
        ]

    elif name == "get_goals":
        status_filter = args.get("status", "all")
        goals = _store["goals"]

        if status_filter != "all":
            goals = [g for g in goals if g.get("status") == status_filter]

        for goal in goals:
            goal["progress_percent"] = round(
                (goal["current_amount"] / goal["target_amount"]) * 100, 1
            )

        return [TextContent(type="text", text=json.dumps({"goals": goals}, indent=2))]

    elif name == "get_analytics":
        month = args.get("month")
        category = args.get("category")

        txns = [t for t in _store["transactions"] if t["type"] == "expense"]

        if month:
            txns = [t for t in txns if t.get("month") == month]

        by_category = defaultdict(float)
        for t in txns:
            by_category[t["category"]] += t["amount"]

        if category:
            cat_txns = [t for t in txns if t["category"] == category]
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "category": category,
                            "total_spent": by_category[category],
                            "transactions": len(cat_txns),
                            "average_transaction": round(
                                by_category[category] / len(cat_txns), 2
                            )
                            if cat_txns
                            else 0,
                        },
                        indent=2,
                    ),
                )
            ]

        total = sum(by_category.values())
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "month": month or "all",
                        "total_spent": total,
                        "by_category": dict(by_category),
                        "top_category": max(by_category, key=by_category.get)
                        if by_category
                        else None,
                    },
                    indent=2,
                ),
            )
        ]

    elif name == "set_budget_alert":
        month = args["month"]
        category = args["category"]
        threshold = args["threshold_percent"]

        if month not in _store["budgets"]:
            return [
                TextContent(
                    type="text",
                    text=json.dumps({"error": "Budget not found"}, indent=2),
                )
            ]

        _store["budgets"][month]["alerts"][category] = threshold

        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "alert_set": True,
                        "month": month,
                        "category": category,
                        "threshold": f"{threshold}%",
                        "tip": f"You'll be warned when {category} spending reaches {threshold}%",
                    },
                    indent=2,
                ),
            )
        ]

    elif name == "get_category_spending":
        month = args.get("month")
        category = args.get("category")

        if not month or not category:
            return [
                TextContent(
                    type="text",
                    text=json.dumps({"error": "month and category required"}, indent=2),
                )
            ]

        txns = [
            t
            for t in _store["transactions"]
            if t["type"] == "expense"
            and t.get("month") == month
            and t.get("category") == category
        ]

        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "category": category,
                        "month": month,
                        "total": sum(t["amount"] for t in txns),
                        "count": len(txns),
                        "transactions": txns,
                    },
                    indent=2,
                ),
            )
        ]

    elif name == "transfer_funds":
        month = args["month"]
        from_cat = args["from_category"]
        to_cat = args["to_category"]
        amount = args["amount"]

        if month not in _store["budgets"]:
            return [
                TextContent(
                    type="text",
                    text=json.dumps({"error": "Budget not found"}, indent=2),
                )
            ]

        budget = _store["budgets"][month]

        if from_cat not in budget["categories"] or to_cat not in budget["categories"]:
            return [
                TextContent(
                    type="text",
                    text=json.dumps({"error": "Invalid category"}, indent=2),
                )
            ]

        budget["categories"][from_cat] -= amount
        budget["categories"][to_cat] += amount

        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "transfer_complete": True,
                        "from": from_cat,
                        "to": to_cat,
                        "amount": amount,
                        "new_allocation": budget["categories"],
                    },
                    indent=2,
                ),
            )
        ]

    elif name == "rollover_unused":
        source_month = args["source_month"]
        target_month = args["target_month"]

        if (
            source_month not in _store["budgets"]
            or target_month not in _store["budgets"]
        ):
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {"error": "Both months must have budgets"}, indent=2
                    ),
                )
            ]

        source = _store["budgets"][source_month]
        target = _store["budgets"][target_month]

        rolled = {}
        for cat in source["categories"]:
            unused = source["categories"][cat] - source["spent"].get(cat, 0)
            if unused > 0:
                rolled[cat] = round(unused, 2)
                target["categories"][cat] += unused
                target["remaining"] += unused

        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "rollover_complete": True,
                        "from": source_month,
                        "to": target_month,
                        "rolled_categories": rolled,
                        "total_rolled": sum(rolled.values()),
                    },
                    indent=2,
                ),
            )
        ]

    return [
        TextContent(type="text", text=json.dumps({"error": "Unknown tool"}, indent=2))
    ]


async def main():
    async with stdio_server(server._read_stream, server._write_stream) as (
        read_stream,
        write_stream,
    ):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="budget-planner-ai",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())