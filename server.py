#!/usr/bin/env python3
"""MEOK AI Labs — budget-planner-ai-mcp MCP Server. Comprehensive budget planning with tracking, goals, and analytics."""

import json
from datetime import datetime, timedelta, timezone
from typing import Any
import uuid
from collections import defaultdict
import sys, os

sys.path.insert(0, os.path.expanduser("~/clawd/meok-labs-engine/shared"))
from auth_middleware import check_access
from mcp.server.fastmcp import FastMCP

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

mcp = FastMCP("budget-planner-ai", instructions="Comprehensive budget planning with tracking, goals, and analytics.")


def create_id():
    return str(uuid.uuid4())[:8]


@mcp.tool()
def create_budget(month: str, income: float, categories: dict, api_key: str = "") -> str:
    """Create a monthly budget with category allocations"""
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return json.dumps({"error": msg, "upgrade_url": "https://meok.ai/pricing"})
    if err := _rl(): return err

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

    return json.dumps(
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
    )


@mcp.tool()
def add_expense(budget_month: str, category: str, amount: float, description: str = "", date: str = "", api_key: str = "") -> str:
    """Record an expense transaction"""
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return json.dumps({"error": msg, "upgrade_url": "https://meok.ai/pricing"})
    if err := _rl(): return err

    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    if budget_month not in _store["budgets"]:
        return json.dumps(
            {"error": f"Budget for {budget_month} not found. Create it first."}, indent=2
        )

    budget = _store["budgets"][budget_month]

    if category not in budget["categories"]:
        return json.dumps(
            {"error": f"Category '{category}' not in budget. Use: {list(budget['categories'].keys())}"},
            indent=2,
        )

    transaction = {
        "id": create_id(),
        "type": "expense",
        "month": budget_month,
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

    return json.dumps(result, indent=2)


@mcp.tool()
def add_income(budget_month: str, source: str, amount: float, date: str = "", api_key: str = "") -> str:
    """Record income for a budget period"""
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return json.dumps({"error": msg, "upgrade_url": "https://meok.ai/pricing"})
    if err := _rl(): return err

    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    if budget_month not in _store["budgets"]:
        return json.dumps({"error": f"Budget for {budget_month} not found"}, indent=2)

    budget = _store["budgets"][budget_month]
    budget["income"] += amount
    budget["remaining"] += amount

    transaction = {
        "id": create_id(),
        "type": "income",
        "month": budget_month,
        "source": source,
        "amount": amount,
        "date": date,
    }
    _store["transactions"].append(transaction)

    return json.dumps(
        {
            "income_recorded": True,
            "transaction_id": transaction["id"],
            "new_total_income": budget["income"],
            "new_remaining": budget["remaining"],
        },
        indent=2,
    )


@mcp.tool()
def get_budget_status(month: str, api_key: str = "") -> str:
    """Get budget status for a month"""
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return json.dumps({"error": msg, "upgrade_url": "https://meok.ai/pricing"})
    if err := _rl(): return err

    if month not in _store["budgets"]:
        return json.dumps({"error": f"Budget for {month} not found"}, indent=2)

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

    return json.dumps(
        {
            "month": month,
            "income": budget["income"],
            "total_allocated": budget["allocated"],
            "total_spent": total_spent,
            "total_remaining": budget["remaining"],
            "categories": category_status,
        },
        indent=2,
    )


@mcp.tool()
def get_transactions(budget_month: str = "", category: str = "", start_date: str = "", end_date: str = "", limit: int = 50, api_key: str = "") -> str:
    """List transactions with optional filters"""
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return json.dumps({"error": msg, "upgrade_url": "https://meok.ai/pricing"})
    if err := _rl(): return err

    txns = _store["transactions"][-limit:]

    if budget_month:
        txns = [t for t in txns if t.get("month") == budget_month]
    if category:
        txns = [t for t in txns if t.get("category") == category]
    if start_date:
        txns = [t for t in txns if t.get("date", "") >= start_date]
    if end_date:
        txns = [t for t in txns if t.get("date", "") <= end_date]

    return json.dumps({"transactions": txns}, indent=2)


@mcp.tool()
def create_goal(name: str, target_amount: float, target_date: str, category: str = "Savings", api_key: str = "") -> str:
    """Create a savings goal"""
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return json.dumps({"error": msg, "upgrade_url": "https://meok.ai/pricing"})
    if err := _rl(): return err

    goal = {
        "id": create_id(),
        "name": name,
        "target_amount": target_amount,
        "target_date": target_date,
        "category": category,
        "current_amount": 0,
        "status": "active",
        "created_at": datetime.now().isoformat(),
    }
    _store["goals"].append(goal)

    return json.dumps(
        {
            "goal_created": True,
            "goal_id": goal["id"],
            "name": goal["name"],
            "target": goal["target_amount"],
            "target_date": goal["target_date"],
        },
        indent=2,
    )


@mcp.tool()
def update_goal_progress(goal_id: str, amount: float, api_key: str = "") -> str:
    """Add contribution to a savings goal"""
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return json.dumps({"error": msg, "upgrade_url": "https://meok.ai/pricing"})
    if err := _rl(): return err

    for goal in _store["goals"]:
        if goal["id"] == goal_id:
            goal["current_amount"] += amount
            if goal["current_amount"] >= goal["target_amount"]:
                goal["status"] = "completed"

            return json.dumps(
                {
                    "updated": True,
                    "goal_id": goal_id,
                    "current": goal["current_amount"],
                    "target": goal["target_amount"],
                    "progress_percent": round(
                        (goal["current_amount"] / goal["target_amount"]) * 100, 1
                    ),
                    "completed": goal["status"] == "completed",
                },
                indent=2,
            )

    return json.dumps({"error": "Goal not found"}, indent=2)


@mcp.tool()
def get_goals(status: str = "all", api_key: str = "") -> str:
    """Get all savings goals with progress"""
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return json.dumps({"error": msg, "upgrade_url": "https://meok.ai/pricing"})
    if err := _rl(): return err

    goals = _store["goals"]

    if status != "all":
        goals = [g for g in goals if g.get("status") == status]

    for goal in goals:
        goal["progress_percent"] = round(
            (goal["current_amount"] / goal["target_amount"]) * 100, 1
        )

    return json.dumps({"goals": goals}, indent=2)


@mcp.tool()
def get_analytics(month: str = "", category: str = "", api_key: str = "") -> str:
    """Get spending analytics"""
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return json.dumps({"error": msg, "upgrade_url": "https://meok.ai/pricing"})
    if err := _rl(): return err

    txns = [t for t in _store["transactions"] if t["type"] == "expense"]

    if month:
        txns = [t for t in txns if t.get("month") == month]

    by_category = defaultdict(float)
    for t in txns:
        by_category[t["category"]] += t["amount"]

    if category:
        cat_txns = [t for t in txns if t["category"] == category]
        return json.dumps(
            {
                "category": category,
                "total_spent": by_category[category],
                "transactions": len(cat_txns),
                "average_transaction": round(by_category[category] / len(cat_txns), 2)
                if cat_txns
                else 0,
            },
            indent=2,
        )

    total = sum(by_category.values())
    return json.dumps(
        {
            "month": month or "all",
            "total_spent": total,
            "by_category": dict(by_category),
            "top_category": max(by_category, key=by_category.get) if by_category else None,
        },
        indent=2,
    )


@mcp.tool()
def set_budget_alert(month: str, category: str, threshold_percent: float, api_key: str = "") -> str:
    """Set spending alert threshold for a category"""
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return json.dumps({"error": msg, "upgrade_url": "https://meok.ai/pricing"})
    if err := _rl(): return err

    if month not in _store["budgets"]:
        return json.dumps({"error": "Budget not found"}, indent=2)

    _store["budgets"][month]["alerts"][category] = threshold_percent

    return json.dumps(
        {
            "alert_set": True,
            "month": month,
            "category": category,
            "threshold": f"{threshold_percent}%",
            "tip": f"You'll be warned when {category} spending reaches {threshold_percent}%",
        },
        indent=2,
    )


@mcp.tool()
def get_category_spending(month: str = "", category: str = "", api_key: str = "") -> str:
    """Get detailed spending by category"""
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return json.dumps({"error": msg, "upgrade_url": "https://meok.ai/pricing"})
    if err := _rl(): return err

    if not month or not category:
        return json.dumps({"error": "month and category required"}, indent=2)

    txns = [
        t
        for t in _store["transactions"]
        if t["type"] == "expense"
        and t.get("month") == month
        and t.get("category") == category
    ]

    return json.dumps(
        {
            "category": category,
            "month": month,
            "total": sum(t["amount"] for t in txns),
            "count": len(txns),
            "transactions": txns,
        },
        indent=2,
    )


@mcp.tool()
def transfer_funds(month: str, from_category: str, to_category: str, amount: float, api_key: str = "") -> str:
    """Transfer between budget categories"""
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return json.dumps({"error": msg, "upgrade_url": "https://meok.ai/pricing"})
    if err := _rl(): return err

    if month not in _store["budgets"]:
        return json.dumps({"error": "Budget not found"}, indent=2)

    budget = _store["budgets"][month]

    if from_category not in budget["categories"] or to_category not in budget["categories"]:
        return json.dumps({"error": "Invalid category"}, indent=2)

    budget["categories"][from_category] -= amount
    budget["categories"][to_category] += amount

    return json.dumps(
        {
            "transfer_complete": True,
            "from": from_category,
            "to": to_category,
            "amount": amount,
            "new_allocation": budget["categories"],
        },
        indent=2,
    )


@mcp.tool()
def rollover_unused(source_month: str, target_month: str, api_key: str = "") -> str:
    """Rollover unused budget to next month"""
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return json.dumps({"error": msg, "upgrade_url": "https://meok.ai/pricing"})
    if err := _rl(): return err

    if source_month not in _store["budgets"] or target_month not in _store["budgets"]:
        return json.dumps({"error": "Both months must have budgets"}, indent=2)

    source = _store["budgets"][source_month]
    target = _store["budgets"][target_month]

    rolled = {}
    for cat in source["categories"]:
        unused = source["categories"][cat] - source["spent"].get(cat, 0)
        if unused > 0:
            rolled[cat] = round(unused, 2)
            target["categories"][cat] += unused
            target["remaining"] += unused

    return json.dumps(
        {
            "rollover_complete": True,
            "from": source_month,
            "to": target_month,
            "rolled_categories": rolled,
            "total_rolled": sum(rolled.values()),
        },
        indent=2,
    )


if __name__ == "__main__":
    mcp.run()
