import nbformat as nbf
nb = nbf.v4.new_notebook(); C = []
md = lambda s: C.append(nbf.v4.new_markdown_cell(s.strip()))
code = lambda s: C.append(nbf.v4.new_code_cell(s.strip()))

md("""
# Analytics Report and Insights Documentation
## Global Superstore - Where is profit growing, and where is it leaking?
*Business analytics report: objectives, analysis, visualizations, insights, executive summary and recommendations.*
""")

md("""
## 1. Business objectives and reporting requirements

**Company context.** Global Superstore is a multinational retailer selling Furniture, Office Supplies and Technology to Consumer, Corporate and Home Office customers
in 7 markets. The dataset covers every order line from **January 2011 to December 2014** (51,290 lines). It is a widely used, fictional business dataset (Tableau Superstore family), so it is suitable for
demonstrating analytics practice but the figures are not a real company's results.

**Business problem.** Leadership wants to know whether the business is growing *profitably*. Sales are clearly rising, but is profit keeping pace, and where is money being lost?

**Stakeholders and what they need**
| Stakeholder | Need |
|---|---|
| Executive team | A clear picture of performance, the main risks and the biggest opportunities |
| Sales and regional managers | Which markets, products and discount practices help or hurt profit |
| Finance | The size of profit leakage and a defensible estimate of the upside from fixing it |
| Operations | Whether shipping practices are cost-efficient |

**Key business questions**
1. How have sales, profit and margin developed over time, and what is driving growth?
2. Which markets, categories and sub-categories create or destroy profit?
3. How do discounts affect profitability?
4. Which customers and countries matter most, and where are the problem areas?
5. Are shipping practices cost-efficient?
6. What should the business do next, in what order, and what is the potential impact?

**Key performance indicators (KPIs)**
| KPI | Definition |
|---|---|
| Sales | Sum of `sales` (net of discount) |
| Profit | Sum of `profit` |
| Profit margin | Profit / Sales |
| Orders | Distinct order IDs |
| Active customers | Distinct customer IDs |
| Average discount | Mean `discount` across order lines |
| Loss-making lines | Share of order lines with negative profit |
| Shipping cost ratio | Shipping cost / Sales |

**Success criteria.** The report must (a) quantify performance with the KPIs above, (b) identify the main drivers of profit and loss, (c) translate findings into prioritised, measurable recommendations,
and (d) be understandable by non-technical readers.
""")

md("## 2. Setup")
code("""
import sys, json
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib.pyplot as plt, matplotlib.ticker as mtick
import seaborn as sns
import plotly.graph_objects as go
from plotly.subplots import make_subplots

ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
sys.path.insert(0, str(ROOT / "src"))
import prep

OUT = ROOT / "outputs"; OUT.mkdir(exist_ok=True)
sns.set_theme(style="whitegrid", context="notebook")
pd.set_option("display.max_columns", 30); pd.set_option("display.width", 200); pd.set_option("display.float_format", "{:,.2f}".format)
BLUE, RED, GREY, GREEN, ORANGE = "#2f6db5", "#d1495b", "#8d99ae", "#3a9d5d", "#f2a541"
R = {}   # every number quoted in the written report is stored here and exported to results.json

def money(x, d=1):   # compact currency formatting
    return f"{x/1e6:,.{d}f}M" if abs(x) >= 1e6 else f"{x/1e3:,.0f}k"
""")

md("## 3. Data understanding, quality audit and preparation")
code("""
raw = prep.load_raw()
print("Rows x columns:", raw.shape)
raw.head(3).T
""")
code("""
audit = {}
audit["rows"], audit["columns"] = raw.shape
# 1. Mixed date formats
pattern = raw["Order Date"].str.contains("-")
audit["dash_format_share"] = float(pattern.mean())
print(f"Order Date uses two formats: 'dd-mm-yyyy' ({pattern.mean():.1%} of rows) and 'd/m/yyyy' ({1 - pattern.mean():.1%}).")
print("Examples:", raw["Order Date"][pattern].iloc[0], "|", raw["Order Date"][~pattern].iloc[0])
df = prep.prepare(raw)                       # strict day-first parsing (raises an error on anything unexpected)
print(f"Parsed range: {df.order_date.min().date()} to {df.order_date.max().date()}")
print(f"Ship days range: {df.ship_days.min()} to {df.ship_days.max()} (negative values: {(df.ship_days < 0).sum()})")

# 2. Missing values
miss = raw.isna().sum(); miss = miss[miss > 0]
audit["postal_code_missing_pct"] = float(raw["Postal Code"].isna().mean() * 100)
print("\\nMissing values:", miss.to_dict(), f"-> Postal Code missing for {audit['postal_code_missing_pct']:.1f}% (non-US addresses); not needed for this analysis")

# 3. Duplicates
audit["exact_duplicates"] = int(raw.duplicated().sum())
same_pair = int(raw.duplicated(subset=["Order ID", "Product ID"]).sum())
audit["repeat_order_product_lines"] = same_pair
print(f"\\nExact duplicate rows: {audit['exact_duplicates']}")
print(f"Order/product pairs appearing on more than one line: {same_pair} (different Row IDs and quantities, i.e. separate order lines, so they are kept)")

# 4. Validity
audit["nonpositive_sales"] = int((df.sales <= 0).sum()); audit["nonpositive_qty"] = int((df.quantity <= 0).sum())
audit["discount_min"], audit["discount_max"] = float(df.discount.min()), float(df.discount.max())
print(f"\\nNon-positive sales: {audit['nonpositive_sales']} | non-positive quantity: {audit['nonpositive_qty']} | discount range: {audit['discount_min']:.0%} to {audit['discount_max']:.0%}")
audit["loss_lines"] = int(df.is_loss.sum()); audit["loss_lines_pct"] = float(df.is_loss.mean() * 100)
print(f"Loss-making order lines: {audit['loss_lines']:,} ({audit['loss_lines_pct']:.1f}%) - a genuine business pattern, so they are kept and analysed rather than removed")
audit["markets"], audit["countries"], audit["products"] = int(df.market.nunique()), int(df.country.nunique()), int(df.product_id.nunique())
R["audit"] = audit
""")
md("""
**Preparation decisions**
| Issue | Decision |
|---|---|
| File encoding is Latin-1, not UTF-8 | Read with `encoding="latin-1"` |
| Two different date formats in the same column | Normalise separators and parse strictly day-first (a unit test covers this) |
| Postal code missing for non-US rows | Not used; excluded from analysis |
| Repeated order/product pairs | Legitimate separate order lines; kept |
| Loss-making lines (about a quarter of lines) | Real business outcome; kept and analysed |
| Derived fields | year, month, quarter, ship days, discount band, loss flag, undiscounted list value |
""")
code("""
df.to_parquet(ROOT / "data" / "superstore_clean.parquet", index=False)
print("Analysis table:", df.shape)
df[["order_date", "market", "category", "sub_category", "sales", "discount", "profit", "ship_mode", "ship_days", "discount_band"]].head()
""")

md("## 4. Performance overview and growth")
md("### 4.1 Headline KPIs")
code("""
overall = prep.kpis(df)
overall["loss_lines_pct"] = df.is_loss.mean() * 100
overall["aov"] = overall["sales"] / overall["orders"]
overall["shipping_cost"] = df.shipping_cost.sum(); overall["shipping_pct_sales"] = overall["shipping_cost"] / overall["sales"] * 100
R["overall"] = overall.to_dict()
tiles = pd.Series({"Sales": f"{overall.sales:,.0f}", "Profit": f"{overall.profit:,.0f}", "Profit margin": f"{overall.margin_pct:.1f}%",
                   "Orders": f"{overall.orders:,.0f}", "Active customers": f"{overall.customers:,.0f}",
                   "Average order value": f"{overall.aov:,.0f}", "Average discount": f"{overall.avg_discount_pct:.1f}%",
                   "Loss-making lines": f"{overall.loss_lines_pct:.1f}%", "Shipping cost / sales": f"{overall.shipping_pct_sales:.1f}%"})
tiles.to_frame("2011-2014 total")
""")
md("### 4.2 Year-on-year trend")
code("""
yearly = df.groupby("year").apply(prep.kpis)
yearly["sales_growth_pct"] = yearly["sales"].pct_change() * 100
yearly["profit_growth_pct"] = yearly["profit"].pct_change() * 100
yearly["aov"] = yearly["sales"] / yearly["orders"]
yearly["orders_per_customer"] = yearly["orders"] / yearly["customers"]
yearly["sales_per_customer"] = yearly["sales"] / yearly["customers"]
first_year = df.groupby("customer_id")["year"].min()
yearly["new_customers"] = [int((first_year == y).sum()) for y in yearly.index]
cagr = (yearly.sales.iloc[-1] / yearly.sales.iloc[0]) ** (1 / 3) - 1
R["yearly"] = yearly.reset_index().to_dict(orient="records"); R["sales_cagr_pct"] = float(cagr * 100)
R["sales_growth_total_pct"] = float((yearly.sales.iloc[-1] / yearly.sales.iloc[0] - 1) * 100)
R["profit_growth_total_pct"] = float((yearly.profit.iloc[-1] / yearly.profit.iloc[0] - 1) * 100)
print(f"Sales CAGR 2011-2014: {cagr:.1%} | total sales growth {R['sales_growth_total_pct']:.0f}% | total profit growth {R['profit_growth_total_pct']:.0f}%")
yearly[["sales", "profit", "margin_pct", "sales_growth_pct", "profit_growth_pct", "orders", "customers", "orders_per_customer", "sales_per_customer", "new_customers"]]
""")
code("""
fig, (axm, ax) = plt.subplots(2, 1, figsize=(9, 6.4), gridspec_kw={"height_ratios": [1, 2.6], "hspace": .12}, sharex=True)
x = np.arange(len(yearly)); w = 0.38
axm.plot(x, yearly.margin_pct, color=RED, marker="o", lw=2.5); axm.set_ylim(8, 15); axm.set_ylabel("Profit margin (%)")
for i, m in enumerate(yearly.margin_pct): axm.text(i, m + .7, f"{m:.1f}%", color=RED, ha="center", fontsize=10)
axm.set_title("Sales and profit have doubled, but profit margin is flat at 11-12%")
ax.bar(x - w / 2, yearly.sales / 1e6, w, color=BLUE, label="Sales")
ax.bar(x + w / 2, yearly.profit / 1e6, w, color=GREEN, label="Profit")
for i, (s_, p_) in enumerate(zip(yearly.sales, yearly.profit)):
    ax.text(i - w / 2, s_ / 1e6 + .05, f"{s_/1e6:.2f}M", ha="center", fontsize=9); ax.text(i + w / 2, p_ / 1e6 + .05, f"{p_/1e6:.2f}M", ha="center", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels(yearly.index); ax.set_ylabel("Millions"); ax.set_ylim(0, yearly.sales.max() / 1e6 * 1.15); ax.legend(loc="upper left")
fig.savefig(OUT / "fig01_yearly_performance.png", dpi=150, bbox_inches="tight"); plt.show()
""")
md("### 4.3 What is driving growth?")
code("""
drivers = yearly[["orders", "customers", "orders_per_customer", "aov", "sales_per_customer", "new_customers"]].copy()
change = (drivers.iloc[-1] / drivers.iloc[0] - 1) * 100
R["growth_drivers_pct"] = change.round(1).to_dict()
print("Change 2011 -> 2014 (%):"); print(change.round(1).to_string())
print(f"\\nOnly {int(yearly.new_customers.iloc[-1])} first-time customers appeared in 2014; the customer base ({int(df.customer_id.nunique()):,} in total) has almost stopped growing.")
drivers
""")
md("""
**Reading the numbers:** order volume almost doubled (+92%) while the number of active customers grew only 15%, so growth comes from **existing customers ordering more often** (orders per customer +67%), not from winning new customers.
Average order value is broadly stable. This matters: growth that depends on a saturated customer base is fragile.
""")

md("### 4.4 Seasonality")
code("""
monthly = df.groupby(["year", "month"])["sales"].sum().unstack()
season = (monthly.div(monthly.sum(axis=1), axis=0) * 100).mean()
quarter = df.groupby("quarter")["sales"].sum(); q_share = quarter / quarter.sum() * 100
R["season_month_share_pct"] = season.round(2).to_dict(); R["quarter_share_pct"] = q_share.round(1).to_dict()
R["nov_dec_share_pct"] = float(season[[11, 12]].sum()); R["jan_feb_share_pct"] = float(season[[1, 2]].sum())
fig, axes = plt.subplots(1, 2, figsize=(13, 4.6), gridspec_kw={"width_ratios": [1.5, 1]})
sns.heatmap(monthly / 1e3, annot=True, fmt=".0f", cmap="Blues", cbar_kws={"label": "Sales (thousands)"}, ax=axes[0])
axes[0].set(title="Monthly sales (thousands) - every year peaks in Q4", xlabel="Month", ylabel="Year")
axes[1].bar(q_share.index.astype(str).map(lambda q: f"Q{q}"), q_share.values, color=[GREY, GREY, GREY, BLUE])
for i, v in enumerate(q_share.values): axes[1].text(i, v + .5, f"{v:.1f}%", ha="center")
axes[1].set(title="Share of sales by quarter", ylabel="% of total sales", ylim=(0, 42))
fig.tight_layout(); fig.savefig(OUT / "fig02_seasonality.png", dpi=150); plt.show()
print(f"Nov + Dec = {R['nov_dec_share_pct']:.1f}% of annual sales; Jan + Feb = {R['jan_feb_share_pct']:.1f}%")
""")

md("## 5. Markets, products and discounts: where profit is made and lost")
md("### 5.1 Market performance")
code("""
low_disc = df[df.discount <= 0.20]
mk = df.groupby("market", observed=True).apply(prep.kpis)
mk["share_lines_over_30pct_discount"] = df.groupby("market", observed=True)["discount"].apply(lambda s: (s > 0.30).mean() * 100)
mk["margin_at_max_20pct_discount"] = low_disc.groupby("market", observed=True).apply(lambda g: g.profit.sum() / g.sales.sum() * 100)
mk["sales_share_pct"] = mk.sales / mk.sales.sum() * 100
mk = mk.sort_values("sales", ascending=False)
R["markets"] = mk.reset_index().to_dict(orient="records")
mk[["sales", "sales_share_pct", "profit", "margin_pct", "avg_discount_pct", "share_lines_over_30pct_discount", "margin_at_max_20pct_discount"]]
""")
code("""
fig, axes = plt.subplots(1, 2, figsize=(13, 4.8))
order = mk.index
axes[0].barh(order[::-1], mk.sales[::-1] / 1e6, color=BLUE)
for i, (s, p) in enumerate(zip(mk.sales[::-1], mk.profit[::-1])): axes[0].text(s / 1e6 + .05, i, f"{s/1e6:.2f}M sales | {p/1e3:,.0f}k profit", va="center", fontsize=9)
axes[0].set(title="Sales by market (profit shown alongside)", xlabel="Sales (millions)", xlim=(0, mk.sales.max() / 1e6 * 1.6))
xx = np.arange(len(order)); w = .38
axes[1].bar(xx - w / 2, mk.margin_pct, w, color=RED, label="Actual margin")
axes[1].bar(xx + w / 2, mk.margin_at_max_20pct_discount, w, color=GREEN, label="Margin on lines with discount <= 20%")
axes[1].axhline(overall.margin_pct, color="black", ls="--", lw=1); axes[1].text(len(order) - .5, overall.margin_pct + .6, "company average", ha="right", fontsize=8)
axes[1].set_xticks(xx); axes[1].set_xticklabels(order); axes[1].set(title="EMEA's weak margin disappears when discounts are 20% or lower", ylabel="Profit margin (%)", ylim=(0, 31)); axes[1].legend(loc="upper left", fontsize=9, ncol=1, framealpha=.9)
fig.tight_layout(); fig.savefig(OUT / "fig03_markets.png", dpi=150); plt.show()
""")
md("""
**Insight:** EMEA earns by far the weakest margin (5.4%), yet on lines with discounts of 20% or less its margin is 24.6%, among the highest of all markets. EMEA also has the highest average discount (19.6%) and the largest share of lines discounted by more than 30% (32%). Its problem is therefore **discounting behaviour, not the market itself**.
""")

md("### 5.2 Category and sub-category performance")
code("""
cat = df.groupby("category", observed=True).apply(prep.kpis).sort_values("profit", ascending=False)
cat["margin_at_max_20pct_discount"] = low_disc.groupby("category", observed=True).apply(lambda g: g.profit.sum() / g.sales.sum() * 100)
R["categories"] = cat.reset_index().to_dict(orient="records")
sub = df.groupby(["category", "sub_category"], observed=True).apply(prep.kpis).reset_index().sort_values("profit")
sub["avg_discount_pct"] = sub["avg_discount_pct"].astype(float)
R["subcategories"] = sub.to_dict(orient="records")
print("Loss-making sub-categories:", sub.loc[sub.profit < 0, "sub_category"].tolist())
cat[["sales", "profit", "margin_pct", "avg_discount_pct", "margin_at_max_20pct_discount"]]
""")
code("""
fig, ax = plt.subplots(figsize=(10, 6.4))
colors = [RED if p < 0 else BLUE for p in sub.profit]
ax.barh(sub.sub_category, sub.profit / 1e3, color=colors)
for i, (p, m) in enumerate(zip(sub.profit, sub.margin_pct)):
    ax.text(p / 1e3 + (6 if p >= 0 else -6), i, f"{p/1e3:,.0f}k ({m:.1f}%)", va="center", ha="left" if p >= 0 else "right", fontsize=8.5)
ax.axvline(0, color="black", lw=.8); ax.set_xlim(sub.profit.min() / 1e3 * 2.2, sub.profit.max() / 1e3 * 1.25)
ax.set(title="Profit by sub-category: Tables is the only loss-maker", xlabel="Profit (thousands) and margin")
fig.tight_layout(); fig.savefig(OUT / "fig04_subcategory_profit.png", dpi=150); plt.show()
""")
code("""
tables = df[df.sub_category == "Tables"]
tb = tables.groupby("discount_band", observed=True).agg(lines=("sales", "size"), sales=("sales", "sum"), profit=("profit", "sum"))
tb["margin_pct"] = tb.profit / tb.sales * 100
R["tables"] = {"sales": float(tables.sales.sum()), "profit": float(tables.profit.sum()), "avg_discount_pct": float(tables.discount.mean() * 100),
               "share_lines_over_30pct": float((tables.discount > .30).mean() * 100),
               "profit_if_discount_max_20": float(tables.loc[tables.discount <= .2, "profit"].sum()),
               "sales_if_discount_max_20": float(tables.loc[tables.discount <= .2, "sales"].sum())}
print(f"Tables: avg discount {R['tables']['avg_discount_pct']:.0f}% (company {overall.avg_discount_pct:.0f}%), {R['tables']['share_lines_over_30pct']:.0f}% of lines discounted by more than 30%")
tb
""")

md("### 5.3 The discount effect")
code("""
band = df.groupby("discount_band", observed=True).apply(prep.kpis)
band["lines_share_pct"] = band.lines / band.lines.sum() * 100
band["sales_share_pct"] = band.sales / band.sales.sum() * 100
R["discount_bands"] = band.reset_index().astype({"discount_band": str}).to_dict(orient="records")
hi = df[df.discount > 0.20]; lo = df[df.discount <= 0.20]; none = df[df.discount == 0]
R["discount"] = {"lines_over_20_pct": float(len(hi) / len(df) * 100), "lines_over_20": int(len(hi)), "sales_over_20": float(hi.sales.sum()),
                 "profit_over_20": float(hi.profit.sum()), "margin_over_20": float(hi.profit.sum() / hi.sales.sum() * 100),
                 "margin_no_discount": float(none.profit.sum() / none.sales.sum() * 100), "lines_no_discount_pct": float(len(none) / len(df) * 100),
                 "profit_if_loss_removed": float(df.profit.sum() - hi.profit.sum()), "profit_share_lost_pct": float(-hi.profit.sum() / df.profit.sum() * 100),
                 "loss_lines_share_with_over_20_pct": float((hi.profit < 0).mean() * 100),
                 "loss_from_all_loss_lines": float(df.loc[df.profit < 0, "profit"].sum()), "margin_up_to_20": float(lo.profit.sum() / lo.sales.sum() * 100)}
D = R["discount"]
print(f"Lines discounted by more than 20%: {D['lines_over_20']:,} ({D['lines_over_20_pct']:.1f}% of lines) -> profit {D['profit_over_20']:,.0f} on sales of {D['sales_over_20']:,.0f} (margin {D['margin_over_20']:.1f}%)")
print(f"Lines with no discount: {D['lines_no_discount_pct']:.1f}% of lines, margin {D['margin_no_discount']:.1f}%")
print(f"Without the loss on >20% discount lines, profit would be {D['profit_if_loss_removed']:,.0f} instead of {overall.profit:,.0f}")
band[["lines", "lines_share_pct", "sales", "sales_share_pct", "profit", "margin_pct"]]
""")
code("""
fig, axes = plt.subplots(1, 2, figsize=(13, 4.8))
cols = [GREEN if m > 15 else (ORANGE if m > 0 else RED) for m in band.margin_pct]
axes[0].bar(band.index.astype(str), band.margin_pct, color=cols)
for i, m in enumerate(band.margin_pct): axes[0].text(i, m + (3 if m >= 0 else -9), f"{m:.1f}%", ha="center", fontsize=9)
axes[0].axhline(0, color="black", lw=.8); axes[0].set(title="Profit margin by discount level: it turns negative above 20%", xlabel="Discount band", ylabel="Profit margin (%)")
axes[1].bar(band.index.astype(str), band.profit / 1e3, color=[BLUE if p > 0 else RED for p in band.profit])
for i, p in enumerate(band.profit): axes[1].text(i, p / 1e3 + (25 if p >= 0 else -70), f"{p/1e3:,.0f}k", ha="center", fontsize=9)
axes[1].axhline(0, color="black", lw=.8); axes[1].set(title="Profit by discount level (thousands)", xlabel="Discount band", ylabel="Profit (thousands)")
fig.tight_layout(); fig.savefig(OUT / "fig05_discount_effect.png", dpi=150); plt.show()
""")
md("### 5.4 Scenario: what if heavy discounts were capped?")
md("""
**Method and assumptions.** Each order line with a discount above the cap is re-priced to the cap (undiscounted value x (1 - cap)), with unit costs unchanged. Because customers may buy less at higher prices, the scenario
is shown for several **volume-retention** levels (100% = no customers lost, 0% = all affected sales are lost). `sales` is assumed to be net of discount. This is an estimate for planning, not a forecast.
""")
code("""
def cap_scenario(cap, retention):
    aff = df[df.discount > cap]
    capped_sales = (aff.sales / (1 - aff.discount) * (1 - cap)).sum()          # revenue of affected lines at the capped price
    uplift = capped_sales - aff.sales.sum()                                      # extra revenue from capped prices
    base = aff.profit.sum()
    d_profit = retention * (base + uplift) - base                               # change in total profit
    new_sales = df.sales.sum() - aff.sales.sum() + retention * capped_sales      # total sales after the change
    return d_profit, new_sales

rows = []
for cap in (0.20, 0.30):
    for ret in (1.0, 0.75, 0.50, 0.25, 0.0):
        d, ns = cap_scenario(cap, ret)
        rows.append({"discount_cap_pct": int(cap * 100), "volume_retained_pct": int(ret * 100), "profit_change": d,
                     "profit_change_pct_of_total": d / overall.profit * 100, "new_total_profit": overall.profit + d,
                     "new_total_sales": ns, "sales_change_pct": (ns / overall.sales - 1) * 100, "new_margin_pct": (overall.profit + d) / ns * 100})
scen = pd.DataFrame(rows)
R["scenario"] = scen.to_dict(orient="records")
R["scenario_lines_affected"] = {"cap20": int((df.discount > .2).sum()), "cap30": int((df.discount > .3).sum())}
scen
""")
code("""
fig, ax = plt.subplots(figsize=(9, 4.8))
for cap, color in ((20, BLUE), (30, ORANGE)):
    s = scen[scen.discount_cap_pct == cap].sort_values("volume_retained_pct")
    ax.plot(s.volume_retained_pct, s.profit_change / 1e3, marker="o", lw=2.5, color=color, label=f"Cap discounts at {cap}%")
    for _, r in s.iterrows(): ax.text(r.volume_retained_pct, r.profit_change / 1e3 + 25, f"{r.profit_change/1e3:,.0f}k", ha="center", fontsize=8, color=color)
ax.axhline(0, color="black", lw=.8); ax.invert_xaxis()
ax.set(title="Capping discounts raises profit even if many customers walk away", xlabel="Share of affected volume retained (%)", ylabel="Change in total profit (thousands)"); ax.legend()
fig.tight_layout(); fig.savefig(OUT / "fig06_discount_scenario.png", dpi=150); plt.show()
be = scen[scen.discount_cap_pct == 20]
print(f"Cap at 20%: profit rises by {be.loc[be.volume_retained_pct == 100, 'profit_change'].iloc[0]/1e3:,.0f}k if all volume is kept, and by {be.loc[be.volume_retained_pct == 0, 'profit_change'].iloc[0]/1e3:,.0f}k even if ALL affected sales are lost.")
""")
md("""**Key points**
1. The affected lines are loss-making overall, so a cap improves profit **in every scenario**, even if every affected sale is lost.
2. The prudent planning range is the **low-retention rows (0-50%)**: moving a line from, say, 70% off to 20% off more than doubles its price, so much of that volume would realistically be lost. Even there, profit rises by roughly 0.8-0.9M.
3. A **30% cap is a weaker guardrail**: re-priced lines at 30% discount are still loss-making on average, so retaining their volume *reduces* the gain (note the rising line at the 30% cap). A 20% cap is the better threshold.
4. The main risk of the policy is to **sales volume**, not to profit, so it should be introduced with monitoring of volume by customer.""")

md("## 6. Geography, customers and fulfilment")
md("### 6.1 Loss-making countries")
code("""
ct = df.groupby("country").agg(sales=("sales", "sum"), profit=("profit", "sum"), avg_discount=("discount", "mean"), lines=("sales", "size"))
ct["margin_pct"] = ct.profit / ct.sales * 100; ct["avg_discount_pct"] = ct.avg_discount * 100
ct = ct.sort_values("profit")
loss_c = ct[ct.profit < 0]
R["countries"] = {"n_countries": int(len(ct)), "n_loss": int(len(loss_c)), "total_loss": float(loss_c.profit.sum()),
                  "top10_loss": float(loss_c.head(10).profit.sum()), "top10": loss_c.head(10).reset_index().to_dict(orient="records"),
                  "avg_discount_loss_countries_pct": float(df[df.country.isin(loss_c.index)].discount.mean() * 100),
                  "avg_discount_other_countries_pct": float(df[~df.country.isin(loss_c.index)].discount.mean() * 100),
                  "best5": ct.tail(5).iloc[::-1].reset_index().to_dict(orient="records")}
C_ = R["countries"]
print(f"{C_['n_loss']} of {C_['n_countries']} countries lose money (combined loss {C_['total_loss']:,.0f}); the worst 10 account for {C_['top10_loss']:,.0f}.")
print(f"Average discount: {C_['avg_discount_loss_countries_pct']:.1f}% in loss-making countries vs {C_['avg_discount_other_countries_pct']:.1f}% elsewhere")
loss_c.head(10)[["sales", "profit", "margin_pct", "avg_discount_pct"]]
""")
code("""
top = loss_c.head(10).iloc[::-1]
fig, ax = plt.subplots(figsize=(9.5, 5.2))
ax.barh(top.index, top.profit / 1e3, color=RED)
for i, (p, d) in enumerate(zip(top.profit, top.avg_discount_pct)): ax.text(p / 1e3 - 2, i, f"{p/1e3:,.0f}k  (avg discount {d:.0f}%)", va="center", ha="right", fontsize=8.5)
ax.set_xlim(top.profit.min() / 1e3 * 1.75, 5); ax.axvline(0, color="black", lw=.8)
ax.set(title="The ten most loss-making countries", xlabel="Profit (thousands)")
fig.tight_layout(); fig.savefig(OUT / "fig07_loss_countries.png", dpi=150); plt.show()
""")

md("### 6.2 Customers")
code("""
cust = df.groupby("customer_id").agg(sales=("sales", "sum"), profit=("profit", "sum"), orders=("order_id", "nunique"), avg_discount=("discount", "mean")).sort_values("profit", ascending=False)
n = len(cust); k = int(n * 0.2); top20 = cust.head(k)
cum = cust.profit.cumsum() / cust.profit.sum() * 100
neg = cust[cust.profit < 0]
R["customers"] = {"n": int(n), "top20_n": k, "top20_profit_share_pct": float(top20.profit.sum() / cust.profit.sum() * 100),
                  "top20_sales_share_pct": float(top20.sales.sum() / cust.sales.sum() * 100), "n_negative": int(len(neg)),
                  "negative_pct": float(len(neg) / n * 100), "negative_profit": float(neg.profit.sum()),
                  "neg_avg_discount_pct": float(neg.avg_discount.mean() * 100), "pos_avg_discount_pct": float(cust[cust.profit >= 0].avg_discount.mean() * 100),
                  "cum_peak_pct": float(cum.max()), "cum_peak_at_customer_share_pct": float((cum.values.argmax() + 1) / n * 100),
                  "median_orders": float(cust.orders.median())}
Cu = R["customers"]
print(f"Top 20% of customers ({Cu['top20_n']}): {Cu['top20_profit_share_pct']:.1f}% of net profit, {Cu['top20_sales_share_pct']:.1f}% of sales")
print(f"{Cu['n_negative']} customers ({Cu['negative_pct']:.1f}%) are unprofitable, losing {Cu['negative_profit']:,.0f} in total; their average discount is {Cu['neg_avg_discount_pct']:.1f}% vs {Cu['pos_avg_discount_pct']:.1f}% for profitable customers")
seg = df.groupby("segment", observed=True).apply(prep.kpis); R["segments"] = seg.reset_index().to_dict(orient="records")
seg[["sales", "profit", "margin_pct", "customers", "avg_discount_pct"]]
""")
code("""
fig, axes = plt.subplots(1, 2, figsize=(13, 4.8))
xs = np.arange(1, n + 1) / n * 100
axes[0].plot(xs, cum.values, color=BLUE, lw=2.5); axes[0].axhline(100, color=GREY, ls="--", lw=1); axes[0].axvline(20, color=RED, ls=":", lw=1.2)
axes[0].annotate(f"Top 20% of customers\\n= {Cu['top20_profit_share_pct']:.0f}% of profit", xy=(20, Cu["top20_profit_share_pct"]), xytext=(33, 45), arrowprops=dict(arrowstyle="->"), fontsize=10)
axes[0].annotate(f"Unprofitable customers pull the\\ntotal back down to 100%", xy=(95, 102), xytext=(52, 118), arrowprops=dict(arrowstyle="->"), fontsize=9)
axes[0].set(title="Customer profit concentration (Pareto curve)", xlabel="Customers ranked by profit (% of customers)", ylabel="Cumulative share of net profit (%)", ylim=(0, 135))
axes[1].hist(cust.profit.clip(-3000, 6000) / 1e3, bins=50, color=BLUE, edgecolor="white")
axes[1].axvline(0, color=RED, lw=1.5); axes[1].set(title=f"Profit per customer ({Cu['n_negative']} customers are below zero)", xlabel="Customer profit (thousands, clipped at -3k / +6k)", ylabel="Customers")
fig.tight_layout(); fig.savefig(OUT / "fig08_customers.png", dpi=150); plt.show()
""")

md("### 6.3 Shipping and fulfilment")
code("""
sm = df.groupby("ship_mode", observed=True).agg(lines=("sales", "size"), sales=("sales", "sum"), profit=("profit", "sum"),
                                                 shipping_cost=("shipping_cost", "sum"), avg_days=("ship_days", "mean"), min_days=("ship_days", "min"), max_days=("ship_days", "max"))
sm["shipping_pct_sales"] = sm.shipping_cost / sm.sales * 100; sm["margin_pct"] = sm.profit / sm.sales * 100
sm["sales_share_pct"] = sm.sales / sm.sales.sum() * 100; sm["shipping_cost_share_pct"] = sm.shipping_cost / sm.shipping_cost.sum() * 100
sm = sm.loc[["Same Day", "First Class", "Second Class", "Standard Class"]]
express = sm.loc[["Same Day", "First Class"]]
ref = sm.loc["Second Class", "shipping_pct_sales"] / 100
saving = float(((express.shipping_pct_sales / 100 - ref) * express.sales).sum())
R["shipping"] = {"modes": sm.reset_index().to_dict(orient="records"), "express_sales_share_pct": float(express.sales.sum() / df.sales.sum() * 100),
                 "express_cost_share_pct": float(express.shipping_cost.sum() / df.shipping_cost.sum() * 100),
                 "express_cost_ratio_pct": float(express.shipping_cost.sum() / express.sales.sum() * 100),
                 "standard_cost_ratio_pct": float(sm.loc["Standard Class", "shipping_pct_sales"]), "illustrative_saving": saving,
                 "total_shipping_cost": float(df.shipping_cost.sum())}
S = R["shipping"]
print(f"Express modes (Same Day + First Class): {S['express_sales_share_pct']:.1f}% of sales but {S['express_cost_share_pct']:.1f}% of shipping cost")
print(f"Shipping cost / sales: express {S['express_cost_ratio_pct']:.1f}% vs Standard {S['standard_cost_ratio_pct']:.1f}%")
print(f"Illustrative saving if express cost ratios matched Second Class: {saving:,.0f}")
sm[["sales_share_pct", "shipping_cost_share_pct", "shipping_pct_sales", "avg_days", "margin_pct"]]
""")
code("""
fig, axes = plt.subplots(1, 2, figsize=(13, 4.6))
axes[0].bar(sm.index, sm.shipping_pct_sales, color=[RED, ORANGE, GREY, BLUE])
for i, v in enumerate(sm.shipping_pct_sales): axes[0].text(i, v + .3, f"{v:.1f}%", ha="center")
axes[0].set(title="Faster shipping costs far more relative to sales", ylabel="Shipping cost as % of sales")
xx = np.arange(len(sm)); w = .38
axes[1].bar(xx - w / 2, sm.sales_share_pct, w, color=BLUE, label="Share of sales"); axes[1].bar(xx + w / 2, sm.shipping_cost_share_pct, w, color=RED, label="Share of shipping cost")
axes[1].set_xticks(xx); axes[1].set_xticklabels(sm.index); axes[1].set(title="Express modes: 20% of sales, 31% of shipping cost", ylabel="%"); axes[1].legend()
fig.tight_layout(); fig.savefig(OUT / "fig09_shipping.png", dpi=150); plt.show()
""")
md("**Data note:** the dataset does not say whether `profit` already includes shipping cost. Shipping findings are therefore presented as a **cost-efficiency signal** and an illustrative saving, to be validated with Finance.")

md("## 7. Dashboards")
md("A one-page static dashboard (for the report) and an interactive Plotly dashboard (for stakeholders) summarise the KPIs and the main findings.")
code("""
fig = plt.figure(figsize=(17, 10.5)); gs = fig.add_gridspec(3, 6, height_ratios=[0.5, 1.5, 1.5], hspace=.42, wspace=.45)
tiles = [("Sales", f"{overall.sales/1e6:.2f}M", BLUE), ("Profit", f"{overall.profit/1e6:.2f}M", GREEN), ("Profit margin", f"{overall.margin_pct:.1f}%", ORANGE),
         ("Orders", f"{overall.orders:,.0f}", BLUE), ("Customers", f"{overall.customers:,.0f}", BLUE), ("Loss-making lines", f"{overall.loss_lines_pct:.1f}%", RED)]
for i, (t, v, c) in enumerate(tiles):
    ax = fig.add_subplot(gs[0, i]); ax.axis("off")
    ax.add_patch(plt.Rectangle((0, 0), 1, 1, transform=ax.transAxes, color=c, alpha=.12)); ax.add_patch(plt.Rectangle((0, 0), .03, 1, transform=ax.transAxes, color=c))
    ax.text(.5, .62, v, ha="center", va="center", fontsize=22, fontweight="bold", color=c, transform=ax.transAxes); ax.text(.5, .17, t, ha="center", va="center", fontsize=11, transform=ax.transAxes)
ax = fig.add_subplot(gs[1, 0:2]); ax.bar(yearly.index.astype(str), yearly.sales / 1e6, color=BLUE, label="Sales"); ax.bar(yearly.index.astype(str), yearly.profit / 1e6, color=GREEN, width=.45, label="Profit")
ax.set_title("Sales and profit by year (millions)"); ax.legend(fontsize=8)
ax = fig.add_subplot(gs[1, 2:4]); ax.barh(mk.index[::-1], mk.margin_pct[::-1], color=[RED if m < 8 else BLUE for m in mk.margin_pct[::-1]]); ax.axvline(overall.margin_pct, color="black", ls="--", lw=1); ax.set_title("Profit margin by market (%)")
ax = fig.add_subplot(gs[1, 4:6]); ax.bar(band.index.astype(str), band.margin_pct, color=[GREEN if m > 15 else (ORANGE if m > 0 else RED) for m in band.margin_pct]); ax.axhline(0, color="black", lw=.8); ax.set_title("Margin by discount level (%)")
ax = fig.add_subplot(gs[2, 0:2]); tail = sub.head(5).iloc[::-1]; head = sub.tail(5); both = pd.concat([sub.head(4), sub.tail(4)])
ax.barh(both.sub_category, both.profit / 1e3, color=[RED if p < 0 else BLUE for p in both.profit]); ax.set_title("Weakest and strongest sub-categories (profit, k)")
ax = fig.add_subplot(gs[2, 2:4]); ax.bar(season.index.astype(int), season.values, color=[BLUE if m >= 11 else GREY for m in season.index]); ax.set_title("Share of annual sales by month (%)"); ax.set_xticks(range(1, 13))
ax = fig.add_subplot(gs[2, 4:6]); ax.bar(sm.index, sm.shipping_pct_sales, color=[RED, ORANGE, GREY, BLUE]); ax.set_title("Shipping cost as % of sales"); ax.tick_params(axis="x", labelsize=8)
fig.suptitle("Global Superstore 2011-2014 - Performance Dashboard", fontsize=17, fontweight="bold", y=.94)
fig.savefig(OUT / "fig10_dashboard.png", dpi=140, bbox_inches="tight"); plt.show()
""")
code("""
fig = make_subplots(rows=3, cols=3, specs=[[{"type": "indicator"}] * 3, [{"type": "xy", "secondary_y": True}, {"type": "xy"}, {"type": "xy"}], [{"type": "xy"}, {"type": "xy"}, {"type": "xy"}]],
                    row_heights=[.16, .42, .42], vertical_spacing=.14,
                    subplot_titles=("", "", "", "Sales and profit by year", "Profit margin by market (%)", "Margin by discount level (%)",
                                    "Profit by sub-category (k)", "Share of annual sales by month (%)", "Shipping cost as % of sales"))
fig.add_trace(go.Indicator(mode="number", value=overall.sales / 1e6, number={"suffix": "M", "valueformat": ".2f"}, title={"text": "Sales"}), 1, 1)
fig.add_trace(go.Indicator(mode="number", value=overall.profit / 1e6, number={"suffix": "M", "valueformat": ".2f"}, title={"text": "Profit"}), 1, 2)
fig.add_trace(go.Indicator(mode="number", value=overall.margin_pct, number={"suffix": "%", "valueformat": ".1f"}, title={"text": "Profit margin"}), 1, 3)
fig.add_trace(go.Bar(x=yearly.index.astype(str), y=yearly.sales / 1e6, name="Sales (M)", marker_color=BLUE), 2, 1)
fig.add_trace(go.Bar(x=yearly.index.astype(str), y=yearly.profit / 1e6, name="Profit (M)", marker_color=GREEN), 2, 1)
fig.add_trace(go.Bar(x=mk.index, y=mk.margin_pct.round(1), marker_color=[RED if m < 8 else BLUE for m in mk.margin_pct], name="Margin %", showlegend=False), 2, 2)
fig.add_trace(go.Bar(x=band.index.astype(str), y=band.margin_pct.round(1), marker_color=[GREEN if m > 15 else (ORANGE if m > 0 else RED) for m in band.margin_pct], name="Margin %", showlegend=False), 2, 3)
fig.add_trace(go.Bar(y=sub.sub_category, x=(sub.profit / 1e3).round(0), orientation="h", marker_color=[RED if p < 0 else BLUE for p in sub.profit], name="Profit (k)", showlegend=False), 3, 1)
fig.add_trace(go.Bar(x=season.index.astype(int), y=season.round(1).values, marker_color=[BLUE if m >= 11 else GREY for m in season.index], name="% of sales", showlegend=False), 3, 2)
fig.add_trace(go.Bar(x=sm.index, y=sm.shipping_pct_sales.round(1), marker_color=[RED, ORANGE, GREY, BLUE], name="Shipping %", showlegend=False), 3, 3)
fig.update_layout(height=900, title_text="Global Superstore 2011-2014 - Interactive Performance Dashboard", barmode="group", template="plotly_white", legend=dict(orientation="h", y=.66))
fig.write_html(OUT / "interactive_dashboard.html", include_plotlyjs="cdn")
print("Interactive dashboard saved: outputs/interactive_dashboard.html")
""")

md("""
## 8. Business insights - what the results mean
| # | Insight | Evidence | Business impact |
|---|---|---|---|
| 1 | Growth is strong but not yet **more profitable** | Sales and profit both roughly doubled, margin flat at 11-12% | Extra sales are not improving profitability; the business is scaling its leakage along with its revenue |
| 2 | Growth comes from **existing customers ordering more** | Orders per customer rose sharply while new customers fell to a trickle | Heavy reliance on a saturated base is a growth risk |
| 3 | **Discounts above 20% destroy profit** | 22% of order lines are discounted above 20% and lose 815k; margin is 25% with no discount and negative above 20% | The loss on those lines equals 56% of total profit |
| 4 | **EMEA and several countries are discount problems**, not market problems | EMEA margin is 24.6% at discounts of 20% or less (5.4% overall); loss-making countries average a 46.9% discount against 8.3% elsewhere | Fixing pricing governance recovers profit without leaving markets |
| 5 | **Tables** is the only loss-making sub-category | Average discount 29% against 14% company-wide; 23% margin at no discount | A targeted fix on one product line |
| 6 | **Profit is concentrated** in a minority of customers, and some customers are unprofitable | Top 20% of customers produce 63% of profit; 297 customers (19%) lose money and receive an average 29.6% discount versus 12.2% for profitable customers | Protect top customers; renegotiate terms with unprofitable ones |
| 7 | **Express shipping** is expensive relative to its sales | Express modes carry a much larger share of shipping cost than of sales | Opportunity to price or reduce express shipping |
| 8 | **Q4 dominates** the year | Nov and Dec are the two largest months, Jan and Feb the smallest | Inventory and staffing should follow the seasonal curve |
""")

md("## 9. Recommendations")
code("""
sc = scen.set_index(["discount_cap_pct", "volume_retained_pct"])["profit_change"]
recs = pd.DataFrame([
    {"priority": 1, "timeline": "0-3 months", "recommendation": "Introduce discount governance: cap standard discounts at 20% and require approval above it",
     "evidence": f"{D['lines_over_20_pct']:.0f}% of lines are discounted >20% and lose {-D['profit_over_20']:,.0f} overall",
     "estimated_impact": f"+{sc[(20, 0)]/1e3:,.0f}k (all affected sales lost) to +{sc[(20, 50)]/1e3:,.0f}k (50% retained) profit; up to +{sc[(20, 100)]/1e3:,.0f}k if no volume is lost",
     "kpi": "Share of lines >20% discount; margin by discount band"},
    {"priority": 2, "timeline": "0-3 months", "recommendation": "Reprice and re-negotiate the Tables line (limit discounts, review supplier cost)",
     "evidence": f"Tables lose {-R['tables']['profit']:,.0f} with an average discount of {R['tables']['avg_discount_pct']:.0f}%",
     "estimated_impact": f"Remove a {-R['tables']['profit']/1e3:,.0f}k loss (overlaps with #1)", "kpi": "Tables margin; Tables discount"},
    {"priority": 3, "timeline": "3-6 months", "recommendation": "Run pricing reviews for EMEA and the most loss-making countries (Turkey, Nigeria, Netherlands, ...)",
     "evidence": f"{C_['n_loss']} countries lose {-C_['total_loss']:,.0f}; EMEA margin is {mk.loc['EMEA', 'margin_pct']:.1f}% vs {mk.loc['EMEA', 'margin_at_max_20pct_discount']:.1f}% at discounts <=20%",
     "estimated_impact": f"Top-10 loss-making countries lose {-C_['top10_loss']:,.0f} (largely overlaps with #1)", "kpi": "Margin by country; number of loss-making countries"},
    {"priority": 4, "timeline": "3-6 months", "recommendation": "Customer programme: protect the top 20% of customers and set discount terms for unprofitable accounts",
     "evidence": f"Top 20% = {Cu['top20_profit_share_pct']:.0f}% of profit; {Cu['n_negative']} customers lose {-Cu['negative_profit']:,.0f}",
     "estimated_impact": f"Up to {-Cu['negative_profit']/1e3:,.0f}k of customer-level losses addressable (overlaps with #1)", "kpi": "Profit per customer; retention of top 20%"},
    {"priority": 5, "timeline": "3-6 months", "recommendation": "Review express shipping: charge for it, or steer low-priority orders to Standard",
     "evidence": f"Express = {S['express_sales_share_pct']:.0f}% of sales but {S['express_cost_share_pct']:.0f}% of shipping cost",
     "estimated_impact": f"About {S['illustrative_saving']/1e3:,.0f}k (illustrative; validate how profit treats shipping)", "kpi": "Shipping cost % of sales by mode"},
    {"priority": 6, "timeline": "6-12 months", "recommendation": "Restart new-customer acquisition, as growth currently depends on a saturated customer base",
     "evidence": f"New customers fell from {int(yearly.new_customers.iloc[1])} (2012) to {int(yearly.new_customers.iloc[-1])} (2014)",
     "estimated_impact": "Growth resilience (not quantified)", "kpi": "New customers per year"},
    {"priority": 7, "timeline": "6-12 months", "recommendation": "Plan inventory, staffing and promotions around the Q4 peak; use non-discount incentives in the Jan-Feb trough",
     "evidence": f"Q4 = {q_share[4]:.0f}% of sales; Nov+Dec = {R['nov_dec_share_pct']:.0f}%, Jan+Feb = {R['jan_feb_share_pct']:.0f}%",
     "estimated_impact": "Efficiency and service levels (not quantified)", "kpi": "Forecast accuracy; stock-outs in Q4"},
])
recs.to_csv(OUT / "recommendations.csv", index=False)
R["recommendations"] = recs.to_dict(orient="records")
recs[["priority", "timeline", "recommendation", "estimated_impact"]]
""")
md("**Important:** recommendations 1 to 4 address overlapping losses (the same discounted order lines appear in several of them), so their impacts are **not additive**. The cap-at-20% scenario in section 5.4 is the best single estimate of the combined upside.")

md("## 10. Executive summary")
code("""
S_ = f'''
EXECUTIVE SUMMARY - Global Superstore, 2011-2014

Business objective: understand whether growth is profitable and where profit is leaking.

Performance : sales {overall.sales/1e6:.2f}M, profit {overall.profit/1e6:.2f}M, margin {overall.margin_pct:.1f}%.
              Sales grew {R['sales_growth_total_pct']:.0f}% and profit {R['profit_growth_total_pct']:.0f}% between 2011 and 2014 (sales CAGR {R['sales_cagr_pct']:.0f}%), but margin stayed at about 11-12%.
Main finding: discounts above 20% are the biggest source of leakage. {D['lines_over_20_pct']:.0f}% of order lines are discounted that heavily and they lose {-D['profit_over_20']/1e3:,.0f}k,
              equal to {D['profit_share_lost_pct']:.0f}% of total profit. Lines with no discount earn a {D['margin_no_discount']:.0f}% margin.
Where        : EMEA (margin {mk.loc['EMEA', 'margin_pct']:.1f}%), the Tables sub-category (loss {-R['tables']['profit']/1e3:,.0f}k) and {C_['n_loss']} loss-making countries are largely discount-driven.
Customers    : the top 20% of customers produce {Cu['top20_profit_share_pct']:.0f}% of profit; {Cu['n_negative']} customers are unprofitable; only {int(yearly.new_customers.iloc[-1])} new customers were added in 2014.
Upside       : capping discounts at 20% would add roughly {sc[(20, 0)]/1e3:,.0f}k-{sc[(20, 50)]/1e3:,.0f}k profit under cautious assumptions (0%-50% of affected volume retained), and up to {sc[(20, 100)]/1e3:,.0f}k if no volume were lost.
'''
print(S_)
""")
code("""
(OUT / "results.json").write_text(json.dumps(R, indent=2, default=lambda o: float(o) if hasattr(o, "__float__") else str(o)))
print("results.json saved with", len(R), "top-level entries")
""")

md("""
## 11. Limitations
- The dataset is a **fictional** retailer used for training and demonstration; the findings illustrate the analysis method rather than a real company's results.
- The scenario analysis assumes unit costs stay constant and treats `sales` as net of discount; real customer reactions to price changes are uncertain, which is why several volume-retention levels are shown.
- It is not documented whether `profit` includes shipping cost, so shipping findings are indicative.
- Customer counts start in 2011, so "new customers" in 2011 is a baseline (all customers are new in the first year of the data).
- Correlation is not causation: high discounts coincide with losses, and the scenario estimates the effect of removing them under stated assumptions.
""")
nb["cells"] = C
nb["metadata"] = {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python"}}
nbf.write(nb, "notebooks/analytics_report.ipynb"); print("cells", len(C))
