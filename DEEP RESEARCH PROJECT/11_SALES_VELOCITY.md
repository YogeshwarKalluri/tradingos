# PART 11 — SALES VELOCITY

**This is the section that decides the answer, and it is the one most business plans get
wrong. Purchasing is easy. Selling is the constraint.**

## Sell-through curves

| Sold within | Conservative | **Base** | Optimistic |
|---|---:|---:|---:|
| 30 days | 32% | **45%** | 55% |
| 60 days | 56% | **72%** | 81% |
| 90 days | 70% | **86%** | 92% |
| 120 days | 78% | **91%** | 96% |
| 180 days | 84% | **93%** | 98% |
| **Never sells** (salvage only) | **16%** | **7%** | **2%** |
| **Average days to sell** | **78** | **55** | **42** |
| **Turns per year** | **4.7** | **6.6** | **8.7** |

The tail is what hurts. In the base case, **28% of every truck is still sitting at day 60 and
14% at day 90.** Those units are consuming floor space, insurance and capital while earning
nothing, and their eventual sale price is lower than day-one pricing because you will have
marked them down.

Category-level 30-day sale probabilities from Part 5 show where the tail comes from: premium
refrigerator 25%, laundry centre 45%, microwave 55%, dishwasher 58% — versus electric dryer
80% and top-load washer 78%.

## Purchase volume vs what you can actually sell

Modelled with the base-case demand ramp (22 units/month in month 1, +11%/month, single-location
ceiling 220/month):

| Units purchased/mo | Can you sell them? | What happens |
|---:|---|---|
| **50** | Yes, from about month 6 | Comfortable. Inventory ~75 units, 1,000–1,500 sq ft. |
| **100** | Yes, from about month 14 | Comfortable. Inventory ~150 units. |
| **150** | Yes, from about month 18 | Tight. Requires the showroom to be working and B2B active. |
| **250** | **Only with a second location or heavy B2B** | Exceeds the single-site retail ceiling of ~220/month. |
| **350** | **No, not in Metro Detroit from one site** | Requires 2 locations and a real B2B book. |
| **500** | **No** | Requires 3 locations. At this point fixed cost has eaten the margin (Part 10). |

**The most common way this business fails is buying at 250 units/month while selling at 150.**
Inventory balloons, cash disappears into stock that is aging toward salvage, and the operator
— who is looking at a full warehouse and a healthy-looking gross margin — does not realise
they are insolvent until they cannot fund the next truck. My Monte Carlo puts the probability
of the business ceasing operations at some point at **50.9%**, and this is the dominant
mechanism.

## Can you sell 10 / 5 / 3 / 2 / 1 per day?

Assume 26 selling days per month.

| Rate | Units/month | Achievable? | What it requires |
|---|---:|---|---|
| **1/day** | 26 | **Yes, from month 1–2** | Facebook Marketplace alone, owner answering messages |
| **2/day** | 52 | **Yes, by month 5–7** | Marketplace + OfferUp + Google Business Profile, consistent listing discipline |
| **3/day** | 78 | **Yes, by month 9–12** | Above + a physical location people can visit + early B2B |
| **5/day** | 130 | **Yes, by month 16–20** | Showroom, 1 paid employee, established Google reviews, repeat landlords |
| **10/day** | 260 | **Only with 2 locations or a serious B2B book** | Past the single-site retail ceiling. This is where margin collapses (Part 10). |
| 20/day | 520 | **Not realistically in 36 months from $20K** | 3 locations, ~$500K working capital, 10+ FTE |

**Ten per day is the wall.** Not because Metro Detroit cannot absorb 260 units a month — the
region's secondary market is ~10,500 units/month — but because *one operator with one showroom
and a Facebook Marketplace presence* cannot reach that many buyers, and the infrastructure that
does reach them costs more than the extra units contribute.

## The profit curve — the central finding of this study

Base-case steady-state operating profit by volume:

| Trucks/mo | Units/mo | Revenue/mo | **Op profit/mo** | Margin | Paid FTE | Sites |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 47 | $19,740 | $3,729 | 18.9% | 0 | 1 |
| 2 | 94 | $39,480 | $5,705 | 14.4% | 0.2 | 1 |
| 3 | 141 | $59,220 | $7,571 | 12.8% | 0.7 | 1 |
| **4.2** | **199** | **$83,580** | **$10,620** | **12.7%** | **1.5** | **1** |
| 5 | 235 | $98,700 | $1,231 | 1.2% | 4.4 | 2 |
| 7 | 329 | $138,180 | $2,891 | 2.1% | 6.6 | 2 |
| 10 | 470 | $197,400 | **−$443** | −0.2% | 9.8 | 3 |
| 15 | 705 | $296,100 | $199 | 0.1% | 14.2 | 4 |
| 20 | 940 | $394,800 | $842 | 0.2% | 18.6 | 5 |

**Profit peaks at $10,620/month at 199 units/month — about $1.0M of annual revenue — and then
falls off a cliff.**

Profitable bands (op profit ≥ $0): **12–440, 481–660, 701–880 units/month.** Bands covering a
$4,500/month owner salary: **56–220, 368–440, 587–660, 807–880.** The gaps are the fixed-cost
steps — the second location, the first salaried hires, the repair technician, the manager.

**Break-even: 12 units/month** in bootstrap configuration (no showroom, owner unpaid);
**56 units/month** to cover a market-rate owner salary.

## Inventory required to sustain growth

At 6.6 turns/year (55-day average), you must hold roughly **1.8 months of forward sales**:

| Sales rate | Inventory on hand | **Inventory capital at $165/unit** |
|---:|---:|---:|
| 50 u/mo | 90 units | $14,850 |
| 100 u/mo | 180 units | $29,700 |
| 200 u/mo | 360 units | $59,400 |
| 350 u/mo | 630 units | $103,950 |
| 500 u/mo | 900 units | $148,500 |

At the conservative 4.7 turns those figures rise by 42%. **Every unit of growth requires cash
to go into inventory 55 days before it comes back out**, which is why Part 16 shows working
capital, not profit, as the binding constraint on the growth path.

## What this means for the $1M question

$1,000,000 of cumulative profit in 36 months is **$27,800 per month, every month, for three
years, starting from zero.** This business peaks at $10,620/month. There is no volume at which
the base-case cost structure produces $27,800/month — the model's best 36-month cumulative
result across all volumes is **$256,197**.

**Volume is not the lever. Contribution per unit is.** Part 15 shows what has to change.

---

*Model: `models/steady_state.py`, `models/business_model_36mo.py`*
