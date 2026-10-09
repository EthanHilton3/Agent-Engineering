from decimal import Decimal

import pytest

from inventory import Item, Store


def make_store():
    store = Store()
    store.add(Item("AAA-0001", "Bolt", Decimal("2.00"), 10))
    store.add(Item("BBB-0002", "Nut", Decimal("1.00"), 3))
    store.add(Item("CCC-0003", "Washer", Decimal("0.50"), 8))
    return store


def test_add_and_get():
    store = make_store()
    assert store.get("AAA-0001").name == "Bolt"
    assert store.get("ZZZ-9999") is None


def test_adding_same_sku_increases_qty():
    store = make_store()
    store.add(Item("AAA-0001", "Bolt", Decimal("2.00"), 5))
    assert store.get("AAA-0001").qty == 15


def test_add_rejects_bad_sku():
    store = Store()
    item = Item("AAA-0001", "Bolt", Decimal("2.00"), 1)
    item.sku = "bad"
    with pytest.raises(ValueError, match="invalid SKU"):
        store.add(item)


def test_remove_returns_item():
    store = make_store()
    removed = store.remove("BBB-0002")
    assert removed.name == "Nut"
    assert store.get("BBB-0002") is None


def test_remove_unknown_sku_raises():
    store = make_store()
    with pytest.raises(KeyError):
        store.remove("ZZZ-9999")


def test_items_sorted_by_sku():
    store = make_store()
    assert [item.sku for item in store.items()] == ["AAA-0001", "BBB-0002", "CCC-0003"]


def test_total_value():
    # 10 * 2.00 + 3 * 1.00 + 8 * 0.50
    assert make_store().total_value() == Decimal("27.00")


def test_low_stock():
    store = make_store()
    assert [item.sku for item in store.low_stock(5)] == ["BBB-0002"]
    assert [item.sku for item in store.low_stock(9)] == ["BBB-0002", "CCC-0003"]
