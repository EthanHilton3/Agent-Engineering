import json
import re

from tools import ToolBox


one_toolbox = ToolBox()


def _money(amount: float) -> float:
    return round(amount, 2)


def _parse_expenses(expenses_json: str) -> list[dict]:
    """Parse and validate expense records supplied by the model or host."""
    expenses = json.loads(expenses_json)
    if not isinstance(expenses, list) or not expenses:
        raise ValueError("expenses_json must be a non-empty JSON array")

    required = {"merchant", "category", "amount", "reimbursable"}
    for expense in expenses:
        if not isinstance(expense, dict) or not required <= expense.keys():
            raise ValueError(
                "each expense must contain merchant, category, amount, and reimbursable"
            )
        if not isinstance(expense["amount"], (int, float)) or isinstance(expense["amount"], bool):
            raise ValueError("expense amounts must be numbers")
        if not isinstance(expense["reimbursable"], bool):
            raise ValueError("reimbursable must be a boolean")
    return expenses


def _report(expenses_json: str, budget: float) -> dict:
    expenses = _parse_expenses(expenses_json)
    return _report_from_expenses(expenses, budget)


def _report_from_expenses(expenses: list[dict], budget: float) -> dict:
    reimbursable = [expense for expense in expenses if expense["reimbursable"]]
    non_reimbursable = [expense for expense in expenses if not expense["reimbursable"]]
    categories = {expense["category"] for expense in reimbursable}

    total = _money(sum(expense["amount"] for expense in reimbursable))
    category_subtotals = {
        category: _money(
            sum(
                expense["amount"]
                for expense in reimbursable
                if expense["category"] == category
            )
        )
        for category in sorted(categories)
    }
    non_reimbursable_total = _money(
        sum(expense["amount"] for expense in non_reimbursable)
    )

    return {
        "reimbursable_expenses": reimbursable,
        "reimbursable_total": total,
        "category_subtotals": category_subtotals,
        "non_reimbursable_expenses": non_reimbursable,
        "non_reimbursable_total": non_reimbursable_total,
        "budget": _money(budget),
        "remaining_or_over": _money(budget - total),
        "under_budget": total <= budget,
    }


@one_toolbox.tool
def compute_expense_report(expenses_json: str, budget: float) -> str:
    """Compute the complete reimbursement report and return it as JSON."""
    return json.dumps(_report(expenses_json, budget))


def expenses_json_from_task(task_text: str) -> str:
    """Extract the JSON expense array from the current task prompt."""
    match = re.search(r"```json\s*(\[.*?\])\s*```", task_text, re.DOTALL)
    if match is None:
        raise ValueError("task prompt must contain the expenses in a JSON code block")
    expenses_json = match.group(1)
    _parse_expenses(expenses_json)
    return expenses_json


def create_many_toolbox(expenses_json: str) -> ToolBox:
    """Bind narrow tools to the current task's data without exposing that data in schemas."""
    expenses = _parse_expenses(expenses_json)
    toolbox = ToolBox()

    @toolbox.tool
    def list_reimbursable_expenses() -> str:
        """List only the expenses marked as reimbursable."""
        return json.dumps([expense for expense in expenses if expense["reimbursable"]])

    @toolbox.tool
    def list_non_reimbursable_expenses() -> str:
        """List the expenses that should not be included in reimbursement."""
        return json.dumps([expense for expense in expenses if not expense["reimbursable"]])

    @toolbox.tool
    def total_reimbursable_expenses() -> float:
        """Calculate the exact total of all reimbursable expenses."""
        return _money(sum(expense["amount"] for expense in expenses if expense["reimbursable"]))

    @toolbox.tool
    def category_total(category: str) -> float:
        """Calculate the exact reimbursable subtotal for one expense category."""
        if category not in {expense["category"] for expense in expenses}:
            raise ValueError(f"unknown expense category: {category}")
        return _money(
            sum(
                expense["amount"]
                for expense in expenses
                if expense["reimbursable"] and expense["category"] == category
            )
        )

    @toolbox.tool
    def compare_with_budget(budget: float) -> str:
        """Compare the exact reimbursable total with a supplied budget."""
        total = total_reimbursable_expenses()
        return json.dumps({
            "budget": _money(budget),
            "reimbursable_total": total,
            "remaining_or_over": _money(budget - total),
            "under_budget": total <= budget,
        })

    return toolbox
