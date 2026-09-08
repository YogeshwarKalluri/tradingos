# PART 6 — THE MAXIMUM RATIONAL BID

You asked me not to repeat your $8,500. I did not. **My number is $4,500, and for a first lot,
$3,000.** Here is the derivation.

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

- **First-time buyer: expected value turns negative above $4,500.**
- **Experienced operator: expected value turns negative above $7,000.**
- **Your $8,500 has negative expected value for both.**

## HARD MAXIMUM BID

# $4,500

And for a **first** lot, **$3,000.**

Two tests set it:

1. **Expected value must be at least 20% of the capital at risk.** At $4,500 the landed cost
   is $6,700 and an experienced operator's EV is $2,881 — 43% of capital. At $7,000 the EV is
   $131 on $9,450, which is 1.4%. You are not compensated for the work.
2. **The bear case must not take an unacceptable share of a $20,000 bankroll.** It fails this
   test at *every* bid: even at $2,000 the bear loss is $3,054, or 15% of your capital, on one
   truck. **There is no bid on this lot that satisfies both tests.** That, by itself, is the
   answer.

The lower $3,000 first-lot number reflects the 40% weight on the bear case for someone who has
never processed a load. Your first truck is tuition. Pay less for tuition.

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
away, floor-loaded, warehouse-damaged, and priced at two to three times what it is worth to a
Detroit operator. Bid $4,500. You will lose the auction. **Losing that auction is the correct
outcome and costs you nothing.**

Then go do the work in Part 4: build a short-haul Whirlpool/Ohio programme where freight is
$13–$21 per unit instead of $31–$45, and where you negotiate a price instead of bidding against
people whose cost structure beats yours.

---

*Full model: `models/lot_underwriting.py` → `models/outputs/lot_ev_by_bid.csv`*
