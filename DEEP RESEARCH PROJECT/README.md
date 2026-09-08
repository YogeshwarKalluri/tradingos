# DEEP RESEARCH PROJECT
## Appliance Liquidation & Scratch-and-Dent Business — Metro Detroit, Michigan
### Feasibility study: can $20,000 of capital produce $1,000,000+ cumulative profit in 36 months?

**Verdict: NO.** Full reasoning in [`00_EXECUTIVE_SUMMARY.md`](00_EXECUTIVE_SUMMARY.md).

**Verdict on the 47-unit Lowe's B-Stock lot at current market pricing: WALK AWAY.**
See [`05_LOT_UNDERWRITING_47_UNITS.md`](05_LOT_UNDERWRITING_47_UNITS.md) and
[`06_MAXIMUM_BID.md`](06_MAXIMUM_BID.md).

---

## Contents

| Part | File | Question answered |
|---|---|---|
| — | [`00_EXECUTIVE_SUMMARY.md`](00_EXECUTIVE_SUMMARY.md) | Verdict, the 20 required numbers, final YES/NO |
| 1 | [`01_INDUSTRY_RESEARCH.md`](01_INDUSTRY_RESEARCH.md) | Market size, margins, turns, defect rates, freight |
| 2 | [`02_COMPETITOR_RESEARCH.md`](02_COMPETITOR_RESEARCH.md) | 21 real operators; what the winners do differently |
| 3 | [`03_MICHIGAN_MARKET.md`](03_MICHIGAN_MARKET.md) | Metro Detroit saturation, best geography |
| 4 | [`04_SOURCING.md`](04_SOURCING.md) | Every channel, ranked by risk-adjusted profit per truck |
| 5 | [`05_LOT_UNDERWRITING_47_UNITS.md`](05_LOT_UNDERWRITING_47_UNITS.md) | Line-by-line valuation of the actual lot |
| 6 | [`06_MAXIMUM_BID.md`](06_MAXIMUM_BID.md) | The rational maximum bid, derived not asserted |
| 7 | [`07_UNIT_ECONOMICS.md`](07_UNIT_ECONOMICS.md) | Per-category P&L, cost to net profit |
| 8 | [`08_DELIVERY_INSTALL.md`](08_DELIVERY_INSTALL.md) | Michigan rates; outsource vs employ vs hybrid |
| 9 | [`09_WAREHOUSE.md`](09_WAREHOUSE.md) | Facility sizing and real SE Michigan rents |
| 10 | [`10_STAFFING.md`](10_STAFFING.md) | Headcount by volume, real Michigan wages |
| 11 | [`11_SALES_VELOCITY.md`](11_SALES_VELOCITY.md) | The binding constraint on the whole business |
| 12 | [`12_CUSTOMER_ACQUISITION.md`](12_CUSTOMER_ACQUISITION.md) | Real CAC by channel |
| 13 | [`13_B2B_STRATEGY.md`](13_B2B_STRATEGY.md) | Packages, landlords, flippers — velocity vs margin |
| 14 | [`14_36_MONTH_MODEL.md`](14_36_MONTH_MODEL.md) | Month-by-month, three scenarios |
| 15 | [`15_SCENARIOS.md`](15_SCENARIOS.md) | Milestone months; Monte Carlo probabilities |
| 16 | [`16_CAPITAL_REQUIREMENTS.md`](16_CAPITAL_REQUIREMENTS.md) | Working capital by scale; financing reality |
| 17 | [`17_REGULATORY_LEGAL.md`](17_REGULATORY_LEGAL.md) | Michigan licensing, EPA 608, warranty liability |
| 18 | [`18_FAILURE_ANALYSIS.md`](18_FAILURE_ANALYSIS.md) | 20 failure modes scored and mitigated |
| 19 | [`19_KILLCRITIC.md`](19_KILLCRITIC.md) | The case against, made as hard as it can be made |
| 20 | [`20_ALTERNATIVES.md`](20_ALTERNATIVES.md) | 11 alternative uses of $20,000, scored |
| 21 | [`21_EXIT_VALUE.md`](21_EXIT_VALUE.md) | What the business would sell for |
| 22 | [`22_INVESTMENT_COMMITTEE_DECISION.md`](22_INVESTMENT_COMMITTEE_DECISION.md) | BUY / BUILD / MODIFY / WALK AWAY |
| — | [`research/SOURCES.md`](research/SOURCES.md) | Every source, with what was and was not verified |

## Models

All figures in this study are produced by the scripts in `models/`, not typed by hand.

```bash
python3 models/labor_productivity.py     # bottom-up labour standard (drives everything)
python3 models/lot_underwriting.py       # the 47-unit lot: valuation, max bid, EV
python3 models/business_model_36mo.py    # 36-month, 3 scenarios -> outputs/model_*.csv
python3 models/steady_state.py           # truck-rate P&L, break-even, working capital
python3 models/monte_carlo.py            # 4,000 paths -> probability of each profit target
```

Outputs land in `models/outputs/`.

## Evidence standard used

These are kept strictly separate throughout and are never substituted for one another:

- **MSRP / "extended retail"** — the number on the auction manifest. Marketing figure.
- **Retail asking price** — what a live retailer lists the unit at today. Verified.
- **Observed transaction price** — what units actually change hands for. Partly verified.
- **Liquidation acquisition price** — the winning auction bid.
- **Landed cost** — bid + buyer's premium + freight.
- **Gross profit** — revenue less landed cost.
- **Contribution profit** — gross profit less all variable cost.
- **Net operating profit** — contribution less fixed cost, *before* owner pay.
- **Owner compensation** — reported separately and never counted as profit.

Where a number could not be verified from a primary source it is labelled **[ESTIMATE]**
and the derivation is shown. Reddit/forum material is labelled **[ANECDOTAL]**.
