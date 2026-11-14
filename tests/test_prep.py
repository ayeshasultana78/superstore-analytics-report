import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import prep  # noqa: E402


def test_parse_dates_handles_both_formats():
    s = pd.Series(["13-01-2011", "1/1/2011", "21/1/2011", "6/12/2014"])
    out = prep.parse_dates(s)
    assert out.tolist() == pd.to_datetime(["2011-01-13", "2011-01-01", "2011-01-21", "2014-12-06"]).tolist()


def test_parse_dates_rejects_garbage():
    with pytest.raises(ValueError):
        prep.parse_dates(pd.Series(["not a date"]))


def _toy():
    return pd.DataFrame({
        "Row ID": [1, 2], "Order ID": ["A", "B"], "Order Date": ["1/1/2011", "13-01-2011"], "Ship Date": ["5/1/2011", "14-01-2011"],
        "Ship Mode": ["Standard Class", "First Class"], "Customer ID": ["C1", "C2"], "Customer Name": ["x", "y"],
        "Segment": ["Consumer", "Corporate"], "City": ["a", "b"], "State": ["a", "b"], "Country": ["a", "b"],
        "Postal Code": [None, None], "Market": ["US", "EU"], "Region": ["West", "North"], "Product ID": ["P1", "P2"],
        "Category": ["Furniture", "Technology"], "Sub-Category": ["Tables", "Phones"], "Product Name": ["t", "p"],
        "Sales": [80.0, 100.0], "Quantity": [1, 2], "Discount": [0.2, 0.0], "Profit": [-5.0, 20.0],
        "Shipping Cost": [4.0, 6.0], "Order Priority": ["Low", "High"],
    })


def test_prepare_derived_fields():
    df = prep.prepare(_toy())
    assert df["ship_days"].tolist() == [4, 1]
    assert df["is_loss"].tolist() == [True, False]
    assert df["list_sales"].iloc[0] == pytest.approx(100.0)          # 80 / (1 - 0.2)
    assert str(df["discount_band"].iloc[0]) == "11-20%"
    assert str(df["discount_band"].iloc[1]) == "0%"


def test_kpis():
    k = prep.kpis(prep.prepare(_toy()))
    assert k["sales"] == pytest.approx(180.0) and k["profit"] == pytest.approx(15.0)
    assert k["margin_pct"] == pytest.approx(15 / 180 * 100)
    assert k["orders"] == 2
