"""Data loading and preparation for the Global Superstore analytics report."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW_PATH = ROOT / "data" / "superstore_raw.csv"
URL = ("https://raw.githubusercontent.com/pplonski/datasets-for-start/refs/heads/master/"
       "superstore-sales/superstore_dataset2011-2015.csv")
DISCOUNT_BINS = [-0.001, 0.0, 0.10, 0.20, 0.30, 0.50, 1.0]
DISCOUNT_LABELS = ["0%", "1-10%", "11-20%", "21-30%", "31-50%", ">50%"]
COLUMNS = {
    "Row ID": "row_id", "Order ID": "order_id", "Order Date": "order_date", "Ship Date": "ship_date",
    "Ship Mode": "ship_mode", "Customer ID": "customer_id", "Customer Name": "customer_name",
    "Segment": "segment", "City": "city", "State": "state", "Country": "country", "Postal Code": "postal_code",
    "Market": "market", "Region": "region", "Product ID": "product_id", "Category": "category",
    "Sub-Category": "sub_category", "Product Name": "product_name", "Sales": "sales", "Quantity": "quantity",
    "Discount": "discount", "Profit": "profit", "Shipping Cost": "shipping_cost", "Order Priority": "order_priority",
}


def parse_dates(s: pd.Series) -> pd.Series:
    """The source mixes 'dd-mm-yyyy' and 'd/m/yyyy' strings (both day-first). Normalise then parse strictly."""
    return pd.to_datetime(s.str.replace("-", "/", regex=False), format="%d/%m/%Y")


def load_raw(path: Path | None = None) -> pd.DataFrame:
    """Read the raw CSV (Latin-1 encoded); download it once if it is not cached locally."""
    path = path or RAW_PATH
    if not path.exists():
        import urllib.request
        path.parent.mkdir(exist_ok=True)
        urllib.request.urlretrieve(URL, path)
    return pd.read_csv(path, encoding="latin-1")


def prepare(raw: pd.DataFrame) -> pd.DataFrame:
    """Return an analysis-ready table with typed columns and derived business fields."""
    df = raw.rename(columns=COLUMNS).copy()
    df["order_date"] = parse_dates(df["order_date"])
    df["ship_date"] = parse_dates(df["ship_date"])
    for col in ["ship_mode", "segment", "market", "region", "category", "sub_category", "order_priority"]:
        df[col] = df[col].astype("category")
    return df.assign(
        year=lambda d: d["order_date"].dt.year,
        month=lambda d: d["order_date"].dt.month,
        quarter=lambda d: d["order_date"].dt.quarter,
        ship_days=lambda d: (d["ship_date"] - d["order_date"]).dt.days,
        discount_band=lambda d: pd.cut(d["discount"], DISCOUNT_BINS, labels=DISCOUNT_LABELS),
        is_loss=lambda d: d["profit"] < 0,
        list_sales=lambda d: d["sales"] / (1 - d["discount"]),   # undiscounted value (Sales is net of discount)
    )


def kpis(g: pd.DataFrame) -> pd.Series:
    """Standard KPI set for any slice of the data."""
    sales, profit = g["sales"].sum(), g["profit"].sum()
    return pd.Series({
        "sales": sales, "profit": profit, "margin_pct": profit / sales * 100 if sales else np.nan,
        "orders": g["order_id"].nunique(), "customers": g["customer_id"].nunique(), "lines": len(g),
        "avg_discount_pct": g["discount"].mean() * 100,
    })
