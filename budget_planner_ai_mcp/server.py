from mcp.server.fastmcp import FastMCP

mcp = FastMCP("budget-planner")

@mcp.tool()
def calculate_50_30_20(income: float) -> dict:
    """Apply the 50/30/20 budgeting rule."""
    return {
        "income": income,
        "needs_50_percent": round(income * 0.50, 2),
        "wants_30_percent": round(income * 0.30, 2),
        "savings_20_percent": round(income * 0.20, 2),
    }

@mcp.tool()
def plan_categories(income: float, categories: dict) -> dict:
    """Allocate income into custom percentage categories."""
    total_pct = sum(categories.values())
    if total_pct > 100:
        return {"error": "Category percentages exceed 100%", "total_percent": total_pct}
    allocation = {name: round(income * (pct / 100), 2) for name, pct in categories.items()}
    return {"income": income, "total_percent": total_pct, "allocation": allocation}

@mcp.tool()
def check_overspend(planned: dict, actual: dict) -> dict:
    """Compare planned vs actual spending per category."""
    results = {}
    for cat, plan in planned.items():
        spent = actual.get(cat, 0.0)
        diff = spent - plan
        results[cat] = {
            "planned": plan,
            "actual": spent,
            "difference": round(diff, 2),
            "status": "over" if diff > 0 else "under" if diff < 0 else "on_track",
        }
    total_planned = sum(planned.values())
    total_actual = sum(actual.values())
    return {
        "categories": results,
        "total_planned": total_planned,
        "total_actual": total_actual,
        "overall_status": "over" if total_actual > total_planned else "under",
    }

def main():
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()
