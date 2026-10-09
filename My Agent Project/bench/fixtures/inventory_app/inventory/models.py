"""Data model for inventory items."""
import re
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

_SKU_PATTERN = re.compile(r"^[A-Z]{3}-\d{4}$")
_CENT = Decimal("0.01")


def validate_sku(sku):
    """Return the SKU if it is well formed, otherwise raise ValueError."""
    if not isinstance(sku, str) or not _SKU_PATTERN.match(sku):
        raise ValueError(f"invalid SKU: {sku!r}")
    return sku


def money(amount):
    """Round an amount of money to whole cents, with halves rounding up."""
    return Decimal(amount).quantize(_CENT, rounding=ROUND_HALF_UP)


@dataclass
class Item:
    sku: str
    name: str
    price: Decimal
    qty: int = 0

    def __post_init__(self):
        validate_sku(self.sku)
        self.price = Decimal(self.price)
        if self.price < 0:
            raise ValueError("price must not be negative")
        if self.qty < 0:
            raise ValueError("qty must not be negative")

    def line_total(self):
        """Value of the stock held for this item, rounded to cents."""
        return money(self.price * self.qty)
