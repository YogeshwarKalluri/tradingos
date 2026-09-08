# PART 15 — THREE SCENARIOS AND THE PROBABILITY OF EACH TARGET

## Milestone table — the direct answer to your question

**Month in which each cumulative operating-profit level is reached (before owner pay):**

| Milestone | Conservative | **Base** | Optimistic |
|---|:--:|:--:|:--:|
| $250,000 | **never** | **never** *(reaches $237,001 at month 36)* | **month 18** |
| $500,000 | **never** | **never** | **month 24** |
| $750,000 | **never** | **never** | **month 29** |
| **$1,000,000** | **never** | **never** | **month 34** |
| $1,500,000 | **never** | **never** | **never** |

**After a market-rate owner salary**, the optimistic case finishes 36 months at **$953,157** —
so on the measure that actually matters to your net worth, **none of the three scenarios reaches
$1,000,000.**

The base case misses $250,000 by $12,999 — it lands at $237,001. That near-miss is worth
noticing: **the realistic outcome of a well-run version of this business is roughly a quarter
of a million dollars of cumulative operating profit over three years, of which you would draw
most as salary.**

## Monte Carlo — 4,000 simulated paths

The three scenarios above are hand-built conjunctions. To get real probabilities I sampled
every driver independently from triangular distributions spanning the sourced ranges — landed
cost $145–$250 (mode $178, reflecting that the *observed market clearing price* is $230–$290
landed and only disciplined buyers get below $180), merchandise revenue $300–$400, productivity
66–94 units/FTE, demand start 11–33, demand growth 5.5–16%, regional ceiling 170–520,
per-location ceiling 150–290, first-30-day sell-through 30–56%, plus random draws on maximum
locations and credit availability.

### Distribution of 36-month cumulative operating profit

| Percentile | Before owner pay | After market-rate owner salary |
|---|---:|---:|
| P5 | −$15,860 | −$93,331 |
| P25 | −$5,980 | −$44,535 |
| **Median** | **$31,482** | **−$20,949** |
| P75 | $125,882 | $17,882 |
| P95 | $283,183 | $175,183 |
| Mean | $73,271 | — |

### Probability of reaching each target within 36 months

| Cumulative profit | **Before owner pay** | **After owner pay** |
|---|---:|---:|
| Any profit at all (> $0) | **68.3%** | **29.4%** |
| $100,000 | 31.0% | 12.2% |
| **$250,000** | **7.8%** | **1.3%** |
| **$500,000** | **0.05%** | **0.0%** |
| **$750,000** | **0.0%** | **0.0%** |
| **$1,000,000** | **0.0%** *(0 of 4,000 paths)* | **0.0%** |
| $2,000,000 | 0.0% | 0.0% |

**Probability the business ceases operations at some point in 36 months: 50.9%.**
**Probability of an outright loss over 36 months, before owner pay: 31.7%.**
**Probability the owner earns less than a $4,500/month equivalent: 81.1%.**

### Why the optimistic scenario never appears in the simulation

The optimistic case is not one lucky draw. It requires roughly **ten** favourable conditions
to hold simultaneously and persistently: bottom-decile landed cost, top-decile pricing,
top-decile productivity, top-decile demand ramp, top-decile market ceiling, a 2% dead-stock
rate, three locations opened on schedule, no cash crisis, no bad truckload, and no competitive
response. Each is individually plausible. **The joint probability is below 1 in 4,000, which is
what the simulation reports.**

That is the honest reading of the optimistic column in Part 14: it is a demonstration of what
$1M would require, not a forecast.

## What would have to change for $1M to be reachable

Volume cannot do it — the base structure's best possible 36-month result across **all** volumes
up to the Metro Detroit absorption ceiling of 840 units/month is **$256,197**. Holding
everything else and raising only revenue per unit:

| Revenue per unit | Best exit rate | **Best 36-month cumulative** | Clears $1M? |
|---:|---:|---:|:--:|
| $420 (base) | 220 u/mo | $256,197 | no |
| $445 (+6%) | 840 u/mo | $662,256 | no |
| **$470 (+12%)** | **840 u/mo** | **$1,166,441** | **yes** |
| $495 (+18%) | 840 u/mo | $1,670,627 | yes |
| $520 (+24%) | 840 u/mo | $2,174,813 | yes |

**$1M requires a sustained ~12% lift in revenue per unit AND operation at essentially the
entire absorbable secondary-appliance demand of Metro Detroit — 840 units per month, four times
the base case's peak.** Note the discontinuity: at $420/unit the optimum is to stay small
(220 u/mo); at $445 and above it flips to maximum scale. **The business is right on the knife
edge between "stay small and profitable" and "scale and win", and $420 is on the wrong side of
it.**

Concretely, +12% on revenue per unit means some combination of:
- skewing purchases hard toward refrigeration and premium units (Part 7: $396–$1,343 net per
  unit versus −$1 for a microwave),
- selling into Novi/Troy/Rochester Hills rather than Detroit/Warren,
- raising delivery attach from 45% to 60% and protection-plan attach from 15% to 25%,
- and refusing to discount — which is hard when AOK Appliance delivers free above $300.

Each is achievable. **All of them, sustained for three years, while quadrupling volume, from
$20,000 — is not a plan, it is a hope.**

## Honest limitations of this analysis

- The Metro Detroit ceiling of 630–840 units/month rests on my own derivation (0.4 appliance
  purchases per household per year, 15% secondary-market share). It is the weakest number in
  the study.
- The condition distribution for a floor-loaded lot (55/25/12/8) is estimated, not sourced. No
  liquidator publishes defect rates.
- The Michigan per-role wage splits are derived from the BLS MSA mean, not from published
  per-occupation Detroit figures (bls.gov was unreachable from this environment).
- The model assumes no competitive response. In reality, a new operator taking 200 units/month
  out of a market with 25–35 incumbents will provoke one.
- **Every one of those limitations, if wrong, is more likely to make the answer worse than
  better.** The conclusion is robust to the uncertainty.

---

*Model: `models/business_model_36mo.py`, `models/monte_carlo.py`, `models/steady_state.py`.
Raw output: `models/outputs/scenario_summary.json`, `models/outputs/monte_carlo.json`.*
