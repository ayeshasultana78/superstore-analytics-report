# Analytics Report and Insights Documentation - Global Superstore (2011-2014)

A business analytics project that answers one question for leadership: **is the company growing profitably, and where is profit leaking?**
It covers the full reporting workflow: business objectives, data analysis, visualizations and dashboards, business insights, executive summary and prioritised recommendations.

**Data:** Global Superstore sales data (51,290 order lines, 7 markets, 147 countries, 2011-2014). It is a widely used *fictional* retailer dataset, so results illustrate the method rather than a real company.

## Deliverables
| Piece | Location |
|---|---|
| Analysis notebook (executed): objectives, data audit, KPIs, findings, scenario model, recommendations, executive summary | `notebooks/analytics_report.ipynb` (HTML copy in `outputs/`) |
| Static one-page dashboard | `outputs/fig10_dashboard.png` |
| Interactive dashboard (open in a browser) | `outputs/interactive_dashboard.html` |
| 9 report charts | `outputs/fig01_...` to `outputs/fig09_...` |
| Prioritised recommendations table | `outputs/recommendations.csv` |
| All numbers quoted in the report | `outputs/results.json` |
| Tested data-preparation module | `src/prep.py`, `tests/test_prep.py` |

## Business questions answered
1. How have sales, profit and margin developed, and what drives growth?
2. Which markets, categories and sub-categories create or destroy profit?
3. How do discounts affect profitability?
4. Which customers and countries matter most?
5. Are shipping practices cost-efficient?
6. What should the business do, in what order, and with what impact?

## Key findings
- Sales 12.64M, profit 1.47M, margin 11.6%. Sales grew 90% and profit 103% from 2011 to 2014, but the margin stayed at 11-12%.
- Growth comes from existing customers ordering more (orders per customer +66%); new customers fell from 210 (2012) to 15 (2014).
- **Discounts above 20% are the biggest leak:** 22% of order lines lose 815k, equal to 56% of total profit. No-discount lines earn a 25% margin.
- EMEA's margin is 5.4% but 24.6% on lines discounted 20% or less; 29 of 147 countries lose money (average discount 47% vs 8% elsewhere).
- Top 20% of customers = 63% of profit; 297 customers are unprofitable.
- Express shipping is 20% of sales but 31% of shipping cost. Q4 delivers 34% of annual sales.
- **Scenario:** a 20% discount cap adds about 815k-924k profit under cautious assumptions (0%-50% of affected volume retained) and lifts the margin to roughly 20-21%.

## Setup and run
```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m pytest tests/                               # data-preparation tests
jupyter lab                                           # open notebooks/analytics_report.ipynb -> Run All
```
`data/superstore_raw.csv` is included; `prep.load_raw()` downloads it from the public source if missing.

## Data preparation notes
- File is Latin-1 encoded; dates appear in two formats (`dd-mm-yyyy` and `d/m/yyyy`, both day-first) and are parsed strictly and validated.
- Postal code is missing for non-US rows and is not used. No exact duplicates; repeated order/product pairs are separate lines and are kept.
- Loss-making lines (24.5%) are real outcomes and are analysed, not removed.

## Limitations
Fictional dataset; scenario assumes constant unit costs and sales net of discount; the data does not say whether profit includes shipping cost; association is not causation.
