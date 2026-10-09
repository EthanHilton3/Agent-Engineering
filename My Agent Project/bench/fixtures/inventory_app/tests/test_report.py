from decimal import Decimal

from inventory import Item, Store
from inventory.report import format_report


def test_report_lists_items_and_total():
    store = Store()
    store.add(Item("AAA-0001", "Bolt", Decimal("2.00"), 10))
    store.add(Item("BBB-0002", "Nut", Decimal("1.00"), 6))
    report = format_report(store)
    assert "AAA-0001" in report
    assert "Total value: $26.00" in report
    assert "Low stock" not in report


def test_report_flags_low_stock():
    store = Store()
    store.add(Item("AAA-0001", "Bolt", Decimal("2.00"), 10))
    store.add(Item("BBB-0002", "Nut", Decimal("1.00"), 2))
    assert "Low stock: BBB-0002" in format_report(store)


def test_totals():
    # Half-cent unit prices must round up to whole cents: 1.005 -> 1.01, 2.675 -> 2.68.
    store = Store()
    store.add(Item("AAA-0001", "Pin", Decimal("1.005"), 1))
    store.add(Item("BBB-0002", "Tack", Decimal("2.675"), 1))
    report = format_report(store)
    assert "$     1.01" in report
    assert "$     2.68" in report
    assert "Total value: $3.69" in report
