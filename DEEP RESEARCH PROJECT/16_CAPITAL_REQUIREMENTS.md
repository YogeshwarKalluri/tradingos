# PART 16 — CAPITAL REQUIREMENTS AND FINANCING

## Working capital by revenue scale

| Annual revenue | Units/mo | **Inventory** | AR / float | Opex buffer (2 mo) | **TOTAL WORKING CAPITAL** |
|---:|---:|---:|---:|---:|---:|
| $50,000 | 10 | $2,475 | $252 | $6,728 | **$9,455** |
| $100,000 | 20 | $4,950 | $504 | $7,456 | **$12,910** |
| $250,000 | 50 | $12,375 | $1,260 | $8,452 | **$22,087** |
| $500,000 | 99 | $24,502 | $2,495 | $13,636 | **$40,633** |
| **$1,000,000** | **198** | **$49,005** | **$4,990** | **$29,730** | **$83,725** |
| $3,000,000 | 595 | $147,262 | $14,994 | $143,224 | **$305,480** |
| $5,000,000 | 992 | $245,520 | $24,998 | $248,860 | **$519,378** |

Inventory assumes **1.5 months of forward cover at $165/unit landed** (6.6 turns/year). At the
conservative 4.7 turns, every inventory figure rises **42%** — at $3M revenue that is $209,000
instead of $147,000.

## The capital ladder

| From → to | Additional capital needed | Where it comes from | Realistic? |
|---|---:|---|---|
| $20K → $50K revenue | $0 | Retained earnings | **Yes** — months 1–4 |
| $50K → $100K | ~$3,500 | Retained earnings | **Yes** — months 5–9 |
| $100K → $250K | ~$9,000 | Retained earnings | **Yes** — months 10–16 |
| $250K → $500K | ~$18,500 | Retained earnings + small LOC | **Yes** — months 17–24 |
| $500K → $1M | ~$43,000 | **Retained earnings alone is too slow** | **Marginal.** Base case needs a $75K line and still only gets there in month 30+. |
| $1M → $3M | ~$222,000 | **External financing required** | **No, not in 36 months from $20K** |
| $3M → $5M | ~$214,000 | External financing | **No** |

**$20,000 gets you to roughly $500,000 of annual revenue on retained earnings alone, on a
24-month timeline.** Past that, growth is financed or it does not happen.

## Financing options, assessed honestly

| Instrument | Available to you? | Terms | Verdict |
|---|---|---|---|
| **Vendor terms** | **Not at first.** Liquidation lots are prepaid, full stop. B-Stock requires payment before release. | — | **Assume none.** This is the harshest fact in this section: your primary input has zero payment float, so every dollar of inventory is cash out the door before a dollar comes back. |
| **Business credit cards** | Yes, on personal guarantee | 0% intro 12–18 months, then 22–29% | **Useful for the first $10–25K only.** Genuinely how many operators fund truck two. Dangerous past the intro period. |
| **Business line of credit** | **Not in year 1.** Lenders want 2 years of filed returns and revenue history. | Prime + 3–9% | Realistic from **month 18–24** at $25–$75K. This is what the base case models. |
| **SBA 7(a)** | **Not for a startup with no operating history.** | Up to $5M (cumulative 7(a)+504 ceiling raised to $10M as of July 2026). Requires **DSCR ≥ 1.10** and personal guarantee. | **Not year 1.** Viable in year 2–3 once you have filed returns showing DSCR coverage. |
| **SBA CAPLines (Seasonal / Working Capital)** | Same history requirement | Revolving, up to $5M | **The right instrument eventually** — it is designed exactly for inventory and seasonal working capital. Year 3 at the earliest. |
| **SBA 7(a) Working Capital Pilot** | Same | Revolving | Same timing |
| **Inventory financing / asset-based lending** | **Effectively no.** | — | Lenders will not advance against liquidation appliance inventory. It is non-standardised, has no reliable liquidation value, and is physically hard to secure. **Do not plan on it.** |
| **Floor-plan financing** | **No.** | — | Floor plan exists for franchised auto/powersports/marine dealers with manufacturer relationships. It does not exist for independent scratch-and-dent appliance liquidators. |
| **Purchase-order financing** | **No.** | — | PO financing needs a creditworthy buyer's purchase order. Retail consumers do not issue POs. **The one exception: a large property-management contract could, in principle, be PO-financed.** That is a real reason to build the B2B book. |
| **Equipment financing** | Yes | 5–8 yrs, 8–14% | Fine for the forklift and box truck. **Do not use it for inventory.** |

## The uncomfortable conclusion

**You cannot borrow your way to $1M of profit in 36 months, because the two forms of debt that
would matter — inventory financing and vendor terms — do not exist in this industry.**

Every other instrument in the table either requires two years of operating history (LOC, SBA)
or funds equipment rather than inventory. That leaves you compounding retained earnings against
a $126.50 contribution margin and a 55-day cash cycle. The compounding is real but slow, and it
is exactly what the base case in Part 14 shows: $20,000 becomes about $500K of annual revenue
in 24 months and about $1.05M in 36.

## What starting capital I would actually require

| | Amount | Why |
|---|---:|---|
| First 2–3 truckloads at a disciplined price | $18,000 | ~$6,000/load landed at a $4,500 bid |
| Facility deposit + first/last (1,000–1,500 sq ft) | $4,000 | |
| **Testing infrastructure** (240V circuits, water, drain) | $6,000 | Deferring this is how the bear case happens |
| Dollies, hand tools, cleaning supplies, straps | $2,000 | |
| Insurance, licences, LLC ($50 LARA), sales tax registration | $2,500 | |
| Listing/inventory software, camera, lighting | $1,500 | |
| **Operating reserve — 3 months of fixed cost** | $9,000 | |
| Contingency for one bad truckload | $5,000 | The bear case is −$5,804 on a $4,500 bid |
| **TOTAL** | **$48,000** | |

**Required starting capital: $45,000–$60,000.**

$20,000 is enough to start **only** in the garage/self-storage configuration: no showroom, no
gas testing, no forklift, one truckload at a time, and no margin for a single bad load. **The
Monte Carlo's 50.9% closure rate is substantially a story about being undercapitalised** — the
paths that die are the ones where a bad load or a slow quarter arrives before the buffer exists.

If $20,000 is genuinely all the capital available, the correct move is not to buy a truckload.
It is to **buy 8–12 individual units from local retailer closeouts and builder overstock,
process and sell them, and learn your actual sell-through and defect rates on $3,000 of risk
instead of $11,000.**

---

*Model: `models/steady_state.py` → `models/outputs/working_capital.csv`.
Sources: [`research/SOURCES.md`](research/SOURCES.md)*
