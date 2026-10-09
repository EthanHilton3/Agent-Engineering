# Inventory App

A small in-memory inventory library used for demos.

## Layout

- `inventory/models.py` - the `Item` dataclass and SKU validation.
- `inventory/store.py` - `Store`, which holds items keyed by SKU.
- `inventory/report.py` - plain-text stock report.
- `inventory/config.py` - tunable settings.

## SKUs

A SKU has three capital letters, a dash, and four digits, e.g. `ABC-1234`.

## Running the tests

    python -m pytest -q
