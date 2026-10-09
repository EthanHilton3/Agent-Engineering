"""Plain-text stock report."""
from .config import CURRENCY_SYMBOL, LOW_STOCK_THRESHOLD


def format_report(store):
    lines = ["SKU       Name            Qty      Value"]
    for item in store.items():
        lines.append(
            f"{item.sku:<9} {item.name:<15} {item.qty:>3} {CURRENCY_SYMBOL}{item.line_total():>9}"
        )
    lines.append(f"Total value: {CURRENCY_SYMBOL}{store.total_value()}")
    low = store.low_stock(LOW_STOCK_THRESHOLD)
    if low:
        lines.append("Low stock: " + ", ".join(item.sku for item in low))
    return "\n".join(lines)
