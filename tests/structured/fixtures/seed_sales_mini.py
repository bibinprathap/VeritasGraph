"""Load sales_mini into one engine: 3 target lines summing to the golden value, 4 decoys."""

from __future__ import annotations

import argparse
import datetime as dt
from decimal import Decimal

import sqlalchemy as sa

ENGINES = {  # key: (product, golden)
    "postgresql": ("Probe Widget PG", Decimal("588.80")), "mysql": ("Probe Widget MY", Decimal("412.50")),
    "clickhouse": ("Probe Widget CH", Decimal("300.00")), "trino": ("Probe Widget TR", Decimal("950.40")),
    "duckdb": ("Probe Widget DD", Decimal("215.10")), "sqlite": ("Probe Widget SL", Decimal("49.99")),
    "snowflake": ("Probe Widget SF", Decimal("77.25")), "databricks": ("Probe Widget DBX", Decimal("1024.00")),
    "hive": ("Probe Widget KY", Decimal("128.64")),
}


def _split(total: Decimal) -> list[Decimal]:
    a = (total * Decimal("0.5")).quantize(Decimal("0.01"))
    b = (total * Decimal("0.3")).quantize(Decimal("0.01"))
    return [a, b, total - a - b]


def build(metadata: sa.MetaData, clickhouse: bool) -> dict[str, sa.Table]:
    kw = {}
    if clickhouse:
        from clickhouse_sqlalchemy import engines

        kw = {"_engine": lambda pk: engines.MergeTree(order_by=pk)}

    def table(name, pk, *cols):
        args = [sa.Column(pk, sa.Integer, primary_key=True), *cols]
        extra = (kw["_engine"](pk),) if clickhouse else ()
        return sa.Table(name, metadata, *args, *extra)

    return {
        "customers": table("customers", "customer_id", sa.Column("name", sa.String(80)), sa.Column("state", sa.String(40))),
        "products": table("products", "product_id", sa.Column("name", sa.String(80))),
        "invoices": table("invoices", "invoice_id", sa.Column("customer_id", sa.Integer), sa.Column("invoice_date", sa.Date)),
        "invoice_lines": table("invoice_lines", "line_id", sa.Column("invoice_id", sa.Integer),
                               sa.Column("product_id", sa.Integer), sa.Column("quantity", sa.Integer),
                               sa.Column("unit_price", sa.Numeric(10, 2)), sa.Column("extended_price", sa.Numeric(10, 2))),
    }


def seed(dsn: str, engine_key: str) -> Decimal:
    product, golden = ENGINES[engine_key]
    eng = sa.create_engine(dsn)
    md = sa.MetaData()
    tables = build(md, engine_key == "clickhouse")
    md.drop_all(eng)
    md.create_all(eng)
    june, july = dt.date(2015, 6, 15), dt.date(2015, 7, 15)
    target = _split(golden)
    with eng.begin() as c:
        c.execute(tables["customers"].insert(), [
            {"customer_id": 1, "name": "Keystone Supply", "state": "Pennsylvania"},
            {"customer_id": 2, "name": "Buckeye Retail", "state": "Ohio"}])
        c.execute(tables["products"].insert(), [{"product_id": 1, "name": product}, {"product_id": 2, "name": "Filler Bolt"}])
        c.execute(tables["invoices"].insert(), [
            {"invoice_id": 10, "customer_id": 1, "invoice_date": june},
            {"invoice_id": 11, "customer_id": 1, "invoice_date": july},   # wrong month decoy
            {"invoice_id": 12, "customer_id": 2, "invoice_date": june}])  # wrong state decoy
        lines = [{"line_id": i + 1, "invoice_id": 10, "product_id": 1, "quantity": 1, "unit_price": p, "extended_price": p}
                 for i, p in enumerate(target)]
        lines += [{"line_id": 10 + i, "invoice_id": inv, "product_id": 1, "quantity": 1,
                   "unit_price": Decimal("111.11"), "extended_price": Decimal("111.11")}
                  for i, inv in enumerate((11, 11, 12, 12))]
        c.execute(tables["invoice_lines"].insert(), lines)
    return golden


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("engine", choices=sorted(ENGINES))
    ap.add_argument("dsn")
    a = ap.parse_args()
    print(seed(a.dsn, a.engine))
