from decimal import Decimal

import pytest

from inventory.models import Item, money, validate_sku


def test_validate_sku_accepts_good_sku():
    assert validate_sku("ABC-1234") == "ABC-1234"


def test_validate_sku_rejects_bad_sku():
    for bad in ["abc-1234", "AB-1234", "ABC-123", "ABC1234", "ABC-12345", "", None, 42]:
        with pytest.raises(ValueError, match="invalid SKU"):
            validate_sku(bad)


def test_item_converts_price_to_decimal():
    item = Item("ABC-1234", "Widget", "2.50", 3)
    assert item.price == Decimal("2.50")


def test_item_rejects_negative_values():
    with pytest.raises(ValueError):
        Item("ABC-1234", "Widget", Decimal("-1"), 1)
    with pytest.raises(ValueError):
        Item("ABC-1234", "Widget", Decimal("1"), -1)


def test_item_rejects_bad_sku():
    with pytest.raises(ValueError, match="invalid SKU"):
        Item("nope", "Widget", Decimal("1"), 1)


def test_line_total_multiplies_price_and_qty():
    assert Item("ABC-1234", "Widget", Decimal("2.50"), 4).line_total() == Decimal("10.00")


def test_money_keeps_whole_cents():
    assert money(Decimal("3.10")) == Decimal("3.10")
