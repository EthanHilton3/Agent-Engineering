"""In-memory store of inventory items."""
from decimal import Decimal

from .models import validate_sku


class Store:
    def __init__(self):
        self._items = {}

    def add(self, item):
        """Add an item. Adding an existing SKU increases its quantity."""
        validate_sku(item.sku)
        existing = self._items.get(item.sku)
        if existing is None:
            self._items[item.sku] = item
        else:
            existing.qty += item.qty
        return self._items[item.sku]

    def remove(self, sku):
        """Remove an item and return it. Raises KeyError if it is unknown."""
        validate_sku(sku)
        if sku not in self._items:
            raise KeyError(sku)
        return self._items.pop(sku)

    def get(self, sku):
        """Return the item with this SKU, or None."""
        return self._items.get(sku)

    def items(self):
        """All items, sorted by SKU."""
        return [self._items[sku] for sku in sorted(self._items)]

    def total_value(self):
        """Total value of all stock, in dollars."""
        return sum((item.line_total() for item in self._items.values()), Decimal("0.00"))

    def low_stock(self, threshold):
        """Items whose quantity is below the threshold, sorted by SKU."""
        return [item for item in self.items() if item.qty < threshold]
