from fastmcp import FastMCP
import math 

mcp = FastMCP(name="FinanceAssistantMCP")

@mcp.tool
def calculate_interest(principal: float, rate: float, time: int, compound: bool = True) -> float:
    """Calculates simple or compound interest on a principal amount.
    
    Args:
        principal: The initial amount.
        rate: Annual interest rate (as decimal, e.g., 0.05 for 5%).
        time: Number of years.
        compound: If True, calculates compound interest; else simple.
    """
    if compound:
        return principal * math.pow((1 + rate), time) - principal
    else:
        return principal * rate * time

@mcp.tool
def categorize_expenses(expenses: str) -> dict:
    """Categorizes and sums expenses from a comma-separated string (e.g., 'rent:2000,food:800,entertainment:300').
    
    Returns a dict with categories as keys and summed totals as values.
    """
    categories = {}
    for item in expenses.split(','):
        if ':' in item:
            category, amount = item.split(':')
            category = category.strip().lower()
            try:
                amount = float(amount.strip())
                categories[category] = categories.get(category, 0) + amount
            except ValueError:
                pass  # Skip invalid entries
    return categories

@mcp.tool
def project_savings(income: float, monthly_expenses: float, months: int, interest_rate: float = 0.03) -> dict:
    """Projects future savings over months, applying optional interest.
    
    Returns a dict with 'total_savings' and monthly breakdowns.
    """
    net_monthly = income - monthly_expenses
    total_savings = 0
    breakdowns = []
    for month in range(1, months + 1):
        total_savings += net_monthly
        interest = total_savings * (interest_rate / 12)  # Monthly interest
        total_savings += interest
        breakdowns.append(f"Month {month}: {round(total_savings, 2)}")
    return {"total_savings": round(total_savings, 2), "breakdowns": breakdowns}

@mcp.prompt
def budget_plan(income: float, expenses: str, months: int) -> str:
    """You are a personal finance assistant. Your goal is to create a simple budget plan based on the user's income, expenses, and time horizon.

Follow these steps:
1. Use the 'categorize_expenses' tool to group and sum the expenses.
2. Calculate total monthly expenses from the categorized sums.
3. Use the 'project_savings' tool with the net income (income - total expenses), months, and default interest rate.
4. Optionally, use 'calculate_interest' if the user mentions specific savings goals (but default to projections).
5. Provide a structured report with:
   - Expense breakdown
   - Net monthly savings
   - Projected savings over months
   - Tips for improvement (e.g., reduce high categories)

Be helpful, professional, and encouraging."""
    pass  # The prompt is handled by the decorator

if __name__ == "__main__":
    mcp.run(transport="http", port="8080")
