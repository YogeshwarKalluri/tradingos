# PART 18 — FAILURE MODE ANALYSIS

Scored **1–10**. **Probability** = likelihood it occurs in 36 months. **Impact** = severity if
it does. **Detectability** = how easily you would *fail* to see it coming (10 = nearly
invisible until it is too late; 1 = obvious immediately). **Risk score = P × I × D**, max 1,000.

Sorted by risk score. The top five account for most of the 50.9% closure probability in the
Monte Carlo.

| # | Failure mode | P | I | D | **Risk** | Mitigation |
|--:|---|--:|--:|--:|--:|---|
| 1 | **Buying too high.** Contribution collapses from $126.50 to $88/unit if you pay the market clearing price of $230–$290 landed instead of $165. At $191 landed the model is insolvent by month 8. | 9 | 10 | **8** | **720** | Written maximum bid per lot **before** the auction opens, calculated from *your* comps, not the manifest. Never bid above it. Losing auctions is the intended outcome. Track landed cost per unit monthly as your single most important KPI. |
| 2 | **Buying faster than you sell.** Inventory balloons, cash converts into aging stock, gross margin still looks healthy on paper. The classic death. | 8 | 10 | **9** | **720** | Hard rule: never hold more than **2.0 months of trailing sales** in units. Compute days-on-hand weekly. If units-on-hand ÷ trailing-30-day-sales > 2.0, **do not buy**, whatever the auction looks like. |
| 3 | **Sales velocity below plan.** Base case needs 45% sold in 30 days. At 32% (conservative) the business dies. | 7 | 10 | 6 | **420** | Measure 30/60/90-day sell-through by category from truck one. Kill categories that miss (microwaves, dishwashers). Open the B2B release valve at day 60, not day 120. |
| 4 | **Freight destroys margin.** $31–$45/unit on a 480-mile load is 25–35% of contribution. | 8 | 7 | 4 | **224** | Concentric-circle sourcing around Detroit. Whirlpool Michigan/Ohio and GE Louisville before anything east of Pittsburgh. Get a binding freight quote **before** bidding, never after. |
| 5 | **Undercapitalisation.** $20,000 against a $48,000 requirement, with a bear-case single-load loss of $5,804. | 8 | 9 | 3 | **216** | Start with 8–12 individual local units, not a truckload. Do not lease a showroom in year one. Keep 3 months of fixed cost untouched. |
| 6 | **Defective inventory above plan.** 14% salvage instead of 8% turns a $2,354 base-case profit into a $5,804 loss on one load. | 7 | 8 | **7** | **392** | Function-test every unit before listing. Photograph and log condition on arrival. Prefer palletised over floor-loaded at equal price. Refuse unmanifested lots entirely. |
| 7 | **Owner becomes the bottleneck.** The owner is 1.5 FTE of unpaid labour and also the buyer, pricer and closer. Illness, burnout or distraction stops everything. | 8 | 7 | 5 | **280** | Document the process from month one. Hire the first generalist at ~150 units/month. Accept lower margin for institutional resilience. |
| 8 | **Cash-flow shortage at a growth step.** Rent and payroll step up before the volume that funds them arrives. | 7 | 9 | 4 | **252** | Never sign a larger lease or make a hire until trailing 3-month profit covers 1.5× the new fixed cost. This is the rule the model enforces and a real operator will be tempted to break. |
| 9 | **Warehouse cost taken too early.** A 10,000 sq ft lease at $10,000/month against 150 units of demand is $6,000/month of pure loss. | 6 | 9 | 3 | **162** | Facility sized to units on hand at 14 sq ft/unit. No showroom below 80 units/month. Short lease terms with expansion options rather than space you grow into. |
| 10 | **Poor Google/BBB reputation.** Your only pricing power over the Marketplace floor. A verified local competitor carries a **BBB F rating with unanswered complaints**. | 6 | 8 | 5 | **240** | Answer every complaint within 24 hours. Honour warranties beyond the letter. Ask every delivered customer for a review. Treat refunds as marketing spend. |
| 11 | **Warranty and return claims above reserve.** 6% reserve is one unit per truck. | 6 | 6 | 5 | **180** | Test properly. Use a third-party administrator for protection plans — **never self-insure**. Conspicuous, attorney-drafted merchantability disclaimer (Part 17). |
| 12 | **Competition responds.** 25–35 incumbents plus ABC Warehouse. Taking 200 units/month out of the market is noticed. | 6 | 6 | 5 | **180** | Compete on geography (Novi/Troy/Rochester, not Detroit/Warren) and on service, never on price. Build the B2B book they cannot easily poach. |
| 13 | **Repairs become uneconomic.** Control board $320–$520; compressor $700–$1,250 against a $600 sale price. | 6 | 5 | 4 | **120** | Hard rule: **no repair exceeding 25% of expected sale price.** Scrap it, recover the refrigerant, sell the carcass to a repair shop for parts. |
| 14 | **Labour inefficiency.** 66 units/FTE instead of 81 raises payroll per unit from $57 to $70 — 10% of contribution. | 6 | 5 | 6 | **180** | Time-study your own process against the 99-minute standard. Batch tasks (test all, then clean all, then photograph all). Buy proper dollies and a forklift before you buy a showroom. |
| 15 | **Seasonality.** Retail troughs in January–February; peaks March–May and around Memorial Day, Labor Day, Black Friday. | 8 | 4 | 2 | **64** | Buy light in November–December. Use B2B and landlord turnover to fill Q1. Hold cash through the trough. |
| 16 | **Delivery damage.** A dented unit on the customer's driveway is a full refund plus a bad review. | 6 | 5 | 3 | **90** | Outsource to insured contractors (Part 8). Photograph every unit at load-out and at delivery, signed by the customer. Proper strapping and stair-climbing dollies. |
| 17 | **Inability to scale sourcing.** Winning enough lots *at your price* to sustain 200 units/month is itself hard. | 7 | 6 | 4 | **168** | Do not rely on auctions. Build 3–5 direct programme relationships (Whirlpool/Ohio, regional distributors, builder overstock) in year one. |
| 18 | **Shrinkage and theft.** Appliances are high-value and portable; warehouses are staffed by low-wage employees. | 5 | 4 | **7** | **140** | Serial-number every unit at receipt. Cameras. Cycle counts weekly. Two-person sign-off on load-outs. |
| 19 | **Regulatory hit — refrigerant venting, unlicensed gas work, defective disclaimer.** | 4 | 8 | 6 | **192** | EPA 608 Type I certification. Licensed subcontractors for all gas and hard-wired work. Attorney-reviewed sale documents. Confirm products liability coverage in writing. |
| 20 | **Catastrophic tail — a fire or flood traced to an appliance you sold or connected.** | 2 | 10 | 5 | **100** | The mitigation is entirely insurance and subcontracting discipline. Verify products liability is not excluded. Never let an employee connect gas. |

## The pattern

**The three highest-scoring failures are all invisible on a P&L until it is too late.**

Buying too high (detectability 8), buying faster than you sell (9), and defective inventory (7)
all present as a *healthy gross margin* on the units you have sold, while cash quietly drains
into stock that is aging toward salvage. A liquidation business can show 60% gross margins right
up to the week it cannot fund payroll.

**Three metrics, reviewed weekly, catch all three:**

1. **Landed cost per unit**, by load. If it drifts above $180, stop buying.
2. **Units on hand ÷ trailing-30-day units sold.** If it exceeds 2.0, stop buying.
3. **Percentage of each load still unsold at day 60.** If it exceeds 30%, your buying mix is
   wrong — change categories, not prices.

None of these appear on a standard P&L, and none of them are things a bookkeeper will flag.
**If you build nothing else, build this dashboard before you buy your first truck.**

---

*Probabilities are informed by the Monte Carlo in `models/monte_carlo.py`; impact figures are
from the models throughout. Scoring is my judgement.*
