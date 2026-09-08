# PART 6 — THE MAXIMUM RATIONAL BID

You asked me not to repeat your $8,500. I did not. **My number is $5,500–$6,000 if your capital
can absorb the downside — and on $20,000 it cannot, so on $20,000 the answer is not to bid at
all.** Here is the derivation.

## The equation

```
Profit  =  Revenue
         − freight − unloading − testing − cleaning − repairs − parts − labour
         − warehouse − advertising − payment processing − delivery cost
         − warranty reserve − returns − shrinkage − dead inventory − disposal
         − (Bid × 1.10)                      [B-Stock buyer's premium is 10%]
```

Solving for Bid at each profit target, using the base-case revenue of **$20,475** and the
full cost stack from Part 5:

## Maximum bid by profit target

| Target | **Lean posture** (owner-operator, 2,500 sq ft, owner labour charged at market) | **Scaled posture** (staffed, 5,000 sq ft, 2 trucks/month) |
|---|---:|---:|
| Cash break-even, owner works for free | $10,049 | $7,706 |
| **True break-even, owner paid market rate** | **$6,640** | **$7,706** |
| **10% profit on revenue ($2,048)** | **$4,778** | **$5,845** |
| **20% profit on revenue ($4,095)** | **$2,917** | **$3,983** |
| **30% profit on revenue ($6,143)** | **$1,056** | **$2,122** |
| **$5,000 profit** | **$2,094** | **$3,161** |
| **$10,000 profit** | **impossible (−$2,451)** | **impossible (−$1,385)** |
| **$15,000 profit** | **impossible (−$6,997)** | **impossible (−$5,930)** |

**$10,000 and $15,000 of profit are not achievable on this lot at any price, including free.**
The base-case contribution before the bid is $7,304. Even if Lowe's gave you the truck, paid
the freight, and handed you the keys, you could not make $10,000 on it.

## The expected-value test

A single point estimate is not a decision. Weighting outcomes — 40/45/15 bear/base/bull for a
first-time buyer with no test bench, no repair capability, no delivery infrastructure and no
established demand channel; 20/55/25 for an experienced operator:

*(Grade B — grade unverified. Grade-conditional figures follow below.)*

| Bid | Landed | $/unit | **EV, first-time buyer** | **EV, experienced** | **Worst case** |
|---:|---:|---:|---:|---:|---:|
| $2,000 | $3,950 | $84 | **+$3,136** | +$5,631 | −$3,054 |
| $2,500 | $4,500 | $96 | +$2,586 | +$5,081 | −$3,604 |
| $3,000 | $5,050 | $107 | +$2,036 | +$4,531 | −$4,154 |
| $3,500 | $5,600 | $119 | +$1,486 | +$3,981 | −$4,704 |
| $4,000 | $6,150 | $131 | +$936 | +$3,431 | −$5,254 |
| **$4,500** | **$6,700** | **$143** | **+$386** | **+$2,881** | **−$5,804** |
| $5,000 | $7,250 | $154 | **−$164** | +$2,331 | −$6,354 |
| $6,000 | $8,350 | $178 | −$1,264 | +$1,231 | −$7,454 |
| $7,000 | $9,450 | $201 | −$2,364 | +$131 | −$8,554 |
| **$8,500** | **$11,100** | **$236** | **−$4,014** | **−$1,519** | **−$10,204** |
| $9,800 | $12,530 | $267 | −$5,444 | −$2,949 | −$11,634 |
| $11,500 | $14,400 | $306 | −$7,314 | −$4,819 | −$13,504 |

- **First-time buyer: expected value turns negative above $4,750** (Grade B).
- **Experienced operator: expected value turns negative above $7,000.**
- **Your $8,500 has negative expected value for both.**

## Grade is the variable that moves the bid most

Defect risk is driven by the **grade** of the load, not by the words "scratch &
dent" on the listing. Wholesaler testing reports claim genuine retailer S&D loads run
~95% "no repairs needed / 5% minor repairs", while customer-return loads can be ~30%
ready-to-sell with ~50% needing a part.

**One refinement matters before you use that number.** The 95% figure is about
**function**, not **cosmetics**. A true S&D load has *more* cosmetic damage than a
customer-return load — cosmetic damage is the reason the unit is in the load at all —
but far fewer functional failures. So a better grade moves units **out of
repairable/salvage and into heavy-cosmetic**; it does not turn the load into clean
units. Reading "95% functional" as "95% sells at full price" is a category error, and
it is the single easiest way to talk yourself into overbidding.

Holding my price deck and cost stack constant and changing only the condition mix:

| Grade | What it is | Condition mix<br>clean / cosmetic / repairable / salvage | Revenue (base) | Bid ceiling<br>(EV ≥ 20% of capital) | Max on a<br>$20k bankroll | Max on a<br>$50k bankroll |
|---|---|:--:|---:|---:|---:|---:|
| **A** | Verified true S&D, palletised, short haul | 57 / 33 / 8 / 2 | $21,435 | **$6,500** | **$3,500** | **$6,500** |
| **A-** **← this lot** | Claimed true S&D, FLOOR-LOADED, 480 mi | 53 / 33 / 10 / 4 | $20,928 | **$6,000** | **$2,500** | **$6,000** |
| **B** | Grade unverified / mixed  (my original base case) | 55 / 25 / 12 / 8 | $20,475 | **$5,500** | **$1,750** | **$5,500** |
| **C** | Customer returns | 60 / 10 / 22 / 8 | $20,977 | **$4,500** | **DO NOT BID** | **$4,250** |
| **D** | Salvage / uninspected | 20 / 15 / 35 / 30 | $15,457 | **DO NOT BID** | **DO NOT BID** | **DO NOT BID** |

The source for the grade distinction is a wholesaler that profits from selling loads,
so the grades above discount its claims rather than adopting them. Even Grade A —
verified, palletised, short-haul — only lifts base-case revenue from $20,475 to
$21,435, because units rescued from salvage arrive in the heavy-cosmetic bucket at 70%
of price, not at full price.

## Two tests, and why they must be kept separate

An earlier draft of this section ran two different questions together and reported a
single number. They are not the same question:

1. **Is the lot worth bidding on?** → expected value ≥ 20% of the capital at risk.
   This is a fact about the lot, and it sets the **bid ceiling** column above.
2. **Can this bankroll absorb the bear case?** → bear-case loss ≤ 15% of total capital.
   This is a fact about **your balance sheet**, not about the lot, and it sets the two
   right-hand columns.

Conflating them produced a number that failed one of its own tests. Separated, they
say something much more useful.

## HARD MAXIMUM BID

For this lot — listed as *Warehouse Damaged / Scratch & Dent*, floor-loaded, grade
**claimed by the seller and not evidenced** — underwrite between Grade A- and Grade B:

# $5,500 – $6,000

**…and on $20,000 of capital, do not bid on this lot at all.**

At a $6,000 bid the Grade A- bear case is **−$6,579**; at $5,500 the Grade B bear case
is **−$6,904**. That is **33–35% of a $20,000 bankroll gone on a single truck.** The
bid ceiling and the bankroll are giving you the same answer Part 16 reaches
independently: **a 47-unit out-of-state truckload is not a $20,000 first purchase.**
Buy 8–12 individual units from local closeouts and builder overstock first, learn your
real sell-through and defect rates on $3,000 of risk, and come back to truckloads with
$45,000–$60,000 behind you.

**Revision note.** An earlier version of this section put the hard maximum at $4,500.
Two corrections moved it: folding in the grade distinction (worth roughly +$500 of
revenue at Grade A-), and separating the lot test from the bankroll test, which had
been collapsed into one figure that failed its own bear-case criterion. **The number
moved up; the recommendation did not change**, because the market is clearing at
$8,841–$11,515 either way.

## What the market is actually doing

Comparable Lowe's scratch-and-dent appliance lots clear at **$188.10–$245.00 per unit**. For
47 units that is **$8,841–$11,515** — before the 10% premium and before your $1,750 of freight,
so **$230–$290 per unit landed.**

**The market is bidding roughly two to three times my maximum.** Three explanations, all of
which are bad news for you:

1. **They are closer.** A buyer 100 miles from Shippensburg pays $400 of freight, not $1,750.
   That is $29/unit of advantage — 23% of the entire contribution margin — before anyone
   competes on anything else.
2. **They price their own labour at zero.** Remove the $3,750 owner-labour charge and the
   break-even bid rises from $6,640 to $10,049, which is inside the observed clearing range.
   **The winning bidders are, in most cases, buying themselves a job and calling the wage
   profit.** Part 19 covers why that distinction matters.
3. **Some of them are losing money and do not know it yet.** In a market where the highest
   bidder wins and unit economics are opaque until the load is processed, the winner's curse
   is severe. Your competitors' bids are not evidence of value.

## The recommendation

**WALK AWAY from this lot.**

Not because scratch-and-dent appliances are a bad business — because *this* lot is 480 miles
away, floor-loaded, of unevidenced grade, and priced at **1.5×–1.9× what it is worth to a Detroit
operator even at the most favourable grade I can defend.** Bid $6,000 if the seller produces a
grading report, $5,500 if not. You will lose the auction. **Losing that auction is the correct
outcome and costs you nothing.**

On $20,000 of capital, do not enter the auction at all: the bear case at those bids is a third
of your bankroll on a single truck.

Then go do the work in Part 4: build a short-haul Whirlpool/Ohio programme where freight is
$13–$21 per unit instead of $31–$45, and where you negotiate a price instead of bidding against
people whose cost structure beats yours.

---

*Full model: `models/lot_underwriting.py` → `models/outputs/lot_ev_by_bid.csv`,
`models/outputs/grade_conditional_bids.csv`*
