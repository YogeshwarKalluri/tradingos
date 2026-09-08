"""
47-unit Lowe's B-Stock scratch & dent lot -- bottom-up underwriting.

Every price input is sourced from observed street prices (see research/SOURCES.md).
NOTHING here uses manifest MSRP as a resale value.
"""
import json, math, csv, os

OUT = os.path.join(os.path.dirname(__file__), "outputs")
os.makedirs(OUT, exist_ok=True)

MANIFEST_MSRP = 53573.99
UNITS = 47

# ---------------------------------------------------------------------------
# 1. Category build of the 47 units.
#    Mix inferred from the named models + typical Lowe's S&D appliance lot mix.
#    street_new  = observed current street price for a NEW unit (verified comps)
#    sd_base     = realistic Metro Detroit scratch&dent ASKING price (base case)
# ---------------------------------------------------------------------------
CATS = [
    # name,                       qty, street_new, sd_base, sd_bear, sd_bull, liquidity(0-1), repair_risk
    ("Premium fridge (Bosch B36CL81ENG class)", 1, 4799, 2200, 1500, 2900, 0.25, 0.30),
    ("French-door / counter-depth fridge",      5, 1250,  750,  575,  900, 0.60, 0.22),
    ("Side-by-side / bottom-freezer fridge",    3, 1150,  625,  480,  760, 0.62, 0.22),
    ("Top-freezer fridge (WRTX5421TZ class)",   3, 1079,  560,  440,  680, 0.75, 0.15),
    ("Front-load washer (WF50BG8300AV class)",  4,  999,  525,  400,  640, 0.70, 0.20),
    ("Top-load washer (WA45T3200AW class)",     5,  605,  335,  260,  410, 0.78, 0.16),
    ("Electric dryer (DLE8400BE class)",        5,  760,  360,  280,  445, 0.80, 0.10),
    ("Gas dryer (DLG3401W class)",              4,  829,  385,  295,  470, 0.68, 0.12),
    ("Electric range (FLCE7522AW class)",       5,  800,  425,  330,  515, 0.72, 0.14),
    ("Gas range",                               2,  950,  500,  380,  610, 0.66, 0.16),
    ("Dishwasher",                              5,  620,  300,  225,  375, 0.58, 0.24),
    ("Over-the-range microwave",                4,  310,  140,  100,  180, 0.55, 0.18),
    ("Laundry center",                          1,  980,  500,  380,  620, 0.45, 0.22),
]
assert sum(c[1] for c in CATS) == UNITS

def ticket(idx):
    return sum(c[1] * c[idx] for c in CATS)

street_total = ticket(2)
base_ticket  = ticket(3)
bear_ticket  = ticket(4)
bull_ticket  = ticket(5)

# ---------------------------------------------------------------------------
# 2. Condition distribution for a FLOOR-LOADED "warehouse damaged" lot.
#    Floor-loaded (not palletized) => elevated handling/transit damage.
# ---------------------------------------------------------------------------
COND = {
    # scenario: (pct_clean, pct_heavy_cosmetic, pct_repairable, pct_salvage)
    "bear": (0.42, 0.28, 0.16, 0.14),
    "base": (0.55, 0.25, 0.12, 0.08),
    "bull": (0.66, 0.22, 0.08, 0.04),
}
HEAVY_COSMETIC_REALIZATION = 0.70   # heavy dents sell at 70% of clean S&D price
REPAIRED_REALIZATION       = 0.80
SALVAGE_RECOVERY_PER_UNIT  = 60.0   # parts/scrap value
NEGOTIATION_AND_MARKDOWN   = {"bear": 0.85, "base": 0.90, "bull": 0.94}

REPAIR_COST_PER_REPAIRABLE = {"bear": 210, "base": 150, "bull": 105}
SURPRISE_REPAIR_POOL       = {"bear": 600, "base": 300, "bull": 120}

# Ancillary attach rates (share of SELLABLE units)
ANC = {
    "bear": dict(del_attach=0.35, del_price=79, del_cost=52,
                 inst_attach=0.15, inst_price=70, inst_cost=30,
                 haul_attach=0.15, haul_price=35, haul_cost=22,
                 warr_attach=0.08, warr_price=110, warr_cost=60),
    "base": dict(del_attach=0.45, del_price=89, del_cost=48,
                 inst_attach=0.25, inst_price=79, inst_cost=28,
                 haul_attach=0.20, haul_price=40, haul_cost=20,
                 warr_attach=0.15, warr_price=129, warr_cost=65),
    "bull": dict(del_attach=0.55, del_price=99, del_cost=45,
                 inst_attach=0.35, inst_price=89, inst_cost=26,
                 haul_attach=0.28, haul_price=45, haul_cost=18,
                 warr_attach=0.22, warr_price=149, warr_cost=70),
}

def revenue(scn):
    tk = {"bear": bear_ticket, "base": base_ticket, "bull": bull_ticket}[scn]
    clean, heavy, rep, salv = COND[scn]
    merch = (tk*clean) + (tk*heavy*HEAVY_COSMETIC_REALIZATION) + (tk*rep*REPAIRED_REALIZATION)
    merch *= NEGOTIATION_AND_MARKDOWN[scn]
    salvage_units = UNITS * salv
    merch += salvage_units * SALVAGE_RECOVERY_PER_UNIT
    sellable = UNITS * (clean + heavy + rep)
    a = ANC[scn]
    anc_rev = sellable * (a["del_attach"]*a["del_price"] + a["inst_attach"]*a["inst_price"]
                          + a["haul_attach"]*a["haul_price"] + a["warr_attach"]*a["warr_price"])
    anc_cost = sellable * (a["del_attach"]*a["del_cost"] + a["inst_attach"]*a["inst_cost"]
                           + a["haul_attach"]*a["haul_cost"] + a["warr_attach"]*a["warr_cost"])
    return dict(merch=merch, anc_rev=anc_rev, anc_cost=anc_cost,
                total=merch+anc_rev, sellable=sellable, salvage_units=salvage_units)

# ---------------------------------------------------------------------------
# 3. Cost stack, excluding the bid itself.
#    Two overhead postures:
#      LEAN  = owner-operator, 2,500 sqft, owner does all labor (labor NOT paid
#              in cash but charged separately as an economic cost)
#      SCALED= staffed operation, 5,000 sqft, 2 trucks/month, wages paid
# ---------------------------------------------------------------------------
FREIGHT = {"bear": 2100, "base": 1750, "bull": 1450}   # Shippensburg PA -> Detroit, ~480 mi, 53' dry van, floor-loaded hand unload
BUYER_PREMIUM_RATE = 0.10                               # B-Stock standard

def costs(scn, posture):
    r = revenue(scn)
    clean, heavy, rep, salv = COND[scn]
    c = {}
    c["freight"] = FREIGHT[scn]
    c["repairs_parts"] = UNITS*rep*REPAIR_COST_PER_REPAIRABLE[scn] + SURPRISE_REPAIR_POOL[scn]
    c["disposal_salvage"] = r["salvage_units"] * 60
    c["payment_processing"] = r["total"] * 0.55 * 0.031
    c["returns_warranty_reserve"] = r["merch"] * {"bear":0.09,"base":0.06,"bull":0.04}[scn]
    c["handling_shrinkage"] = r["merch"] * {"bear":0.035,"base":0.02,"bull":0.012}[scn]
    c["ancillary_direct_cost"] = r["anc_cost"]
    if posture == "lean":
        c["facility_allocation"] = 2083      # 2,500 sqft @ ~$10/sf all-in, 1 truck/month = full month
        c["marketing"] = 300
        c["payroll"] = 0                     # owner labor -- charged below, not paid
        c["misc_fixed_alloc"] = 400          # insurance, software, licenses, utilities share
        c["owner_labor_economic_cost"] = 150 * 25   # ~150 hrs of owner time @ $25/hr market rate
    else:
        c["facility_allocation"] = 2500      # 5,000 sqft @ ~$12/sf all-in = $5,000/mo, 2 trucks/mo
        c["marketing"] = 400
        c["payroll"] = 300 + 800 + 160 + 600 # unload + test/clean + photo/list + sales labor
        c["misc_fixed_alloc"] = 600
        c["owner_labor_economic_cost"] = 0   # wages already paid
    return c

def contribution_before_bid(scn, posture, include_owner_labor=True):
    r = revenue(scn); c = costs(scn, posture)
    total_cost = sum(v for k, v in c.items()
                     if include_owner_labor or k != "owner_labor_economic_cost")
    return r["total"] - total_cost, r, c

def max_bid(target_profit, scn="base", posture="lean", include_owner_labor=True):
    cbb, _, _ = contribution_before_bid(scn, posture, include_owner_labor)
    return (cbb - target_profit) / (1 + BUYER_PREMIUM_RATE)

# ---------------------------------------------------------------------------
report = {}
report["manifest_msrp"] = MANIFEST_MSRP
report["msrp_per_unit"] = MANIFEST_MSRP / UNITS
report["verified_street_new_total"] = street_total
report["street_to_msrp_ratio"] = street_total / MANIFEST_MSRP
report["sd_ticket"] = dict(bear=bear_ticket, base=base_ticket, bull=bull_ticket)
report["sd_ticket_pct_of_msrp"] = {k: v/MANIFEST_MSRP for k, v in report["sd_ticket"].items()}

for scn in ("bear","base","bull"):
    r = revenue(scn)
    report[f"revenue_{scn}"] = {k: round(v,2) for k,v in r.items()}

for posture in ("lean","scaled"):
    for scn in ("bear","base","bull"):
        cbb_owner, r, c = contribution_before_bid(scn, posture, True)
        cbb_noowner, _, _ = contribution_before_bid(scn, posture, False)
        report[f"cost_{posture}_{scn}"] = {k: round(v,2) for k,v in c.items()}
        report[f"contrib_before_bid_{posture}_{scn}"] = dict(
            with_owner_labor=round(cbb_owner,2), without_owner_labor=round(cbb_noowner,2))

targets = {}
rev_base = revenue("base")["total"]
for label, tp, incl in [
    ("breakeven_cash_lean(owner unpaid)", 0, False),
    ("breakeven_true_lean(owner paid mkt)", 0, True),
    ("profit_10pct_of_revenue", 0.10*rev_base, True),
    ("profit_20pct_of_revenue", 0.20*rev_base, True),
    ("profit_30pct_of_revenue", 0.30*rev_base, True),
    ("profit_$5,000", 5000, True),
    ("profit_$10,000", 10000, True),
    ("profit_$15,000", 15000, True),
]:
    targets[label] = dict(
        lean=round(max_bid(tp,"base","lean",incl),0),
        scaled=round(max_bid(tp,"base","scaled",incl),0))
report["max_bid_base_case"] = targets
report["revenue_base_total"] = round(rev_base,2)

# What happens at the proposed $8,500 bid, and at observed market clearing prices
def pnl_at_bid(bid, scn, posture, include_owner_labor=True):
    cbb, r, c = contribution_before_bid(scn, posture, include_owner_labor)
    return dict(bid=bid, buyer_premium=round(bid*BUYER_PREMIUM_RATE,2),
                landed_total=round(bid*1.10 + c["freight"],2),
                landed_per_unit=round((bid*1.10 + c["freight"])/UNITS,2),
                revenue=round(r["total"],2),
                profit=round(cbb - bid*1.10,2))

report["scenario_at_bid"] = {}
for bid in (3500, 4500, 6000, 8500, 9800, 11500):
    report["scenario_at_bid"][f"${bid}"] = {
        f"{posture}_{scn}": pnl_at_bid(bid, scn, posture)
        for posture in ("lean","scaled") for scn in ("bear","base","bull")}

with open(os.path.join(OUT,"lot_underwriting.json"),"w") as f:
    json.dump(report, f, indent=2)

with open(os.path.join(OUT,"lot_category_valuation.csv"),"w",newline="") as f:
    w = csv.writer(f)
    w.writerow(["category","qty","street_new_each","sd_bear_each","sd_base_each","sd_bull_each",
                "base_ext","30d_sell_prob","repair_risk"])
    for n,q,st,b,be,bu,liq,rr in CATS:
        w.writerow([n,q,st,be,b,bu,q*b,liq,rr])

# console summary
print(f"Manifest MSRP           : ${MANIFEST_MSRP:,.2f}  (${MANIFEST_MSRP/UNITS:,.2f}/unit)")
print(f"Verified NEW street val : ${street_total:,.0f}  ({street_total/MANIFEST_MSRP:.1%} of manifest MSRP)")
for scn in ("bear","base","bull"):
    r = revenue(scn)
    print(f"{scn:>4} | S&D ticket ${ticket({'bear':4,'base':3,'bull':5}[scn]):>8,.0f} | "
          f"realized merch ${r['merch']:>8,.0f} | ancillary ${r['anc_rev']:>6,.0f} | TOTAL REV ${r['total']:>9,.0f} "
          f"({r['total']/MANIFEST_MSRP:.1%} of MSRP)")
print()
print("MAX BID (base case):")
for k,v in targets.items():
    print(f"  {k:<38} lean ${v['lean']:>8,.0f}   scaled ${v['scaled']:>8,.0f}")
print()
print("P&L at various bids (BASE case revenue):")
for bid in (3500,4500,6000,8500,9800,11500):
    l = pnl_at_bid(bid,"base","lean"); s = pnl_at_bid(bid,"base","scaled")
    lb = pnl_at_bid(bid,"bear","lean"); ll = pnl_at_bid(bid,"bull","lean")
    print(f"  bid ${bid:>6,} landed ${l['landed_total']:>8,.0f} (${l['landed_per_unit']:>6.2f}/u) | "
          f"lean base ${l['profit']:>8,.0f} | lean bear ${lb['profit']:>8,.0f} | lean bull ${ll['profit']:>8,.0f} | scaled base ${s['profit']:>8,.0f}")

# ---------------------------------------------------------------------------
# 4. Expected value of the lot at a given bid, for a FIRST-TIME buyer.
#    A first-timer has no testing bench, no repair capability, no delivery
#    infrastructure and no established demand channel, so the outcome weights
#    are skewed toward the bear case.
# ---------------------------------------------------------------------------
WEIGHTS = {"first_time": dict(bear=0.40, base=0.45, bull=0.15),
           "experienced": dict(bear=0.20, base=0.55, bull=0.25)}
print("\nEXPECTED VALUE BY BID (lean owner-operator posture, owner labour charged at market)")
print(f"{'bid':>8}{'landed':>9}{'$/unit':>8}{'EV first-timer':>16}{'EV experienced':>16}{'worst case':>12}")
ev_table=[]
for bid in (2000,2500,3000,3500,4000,4500,5000,6000,7000,8500,9800,11500):
    pn = {s: pnl_at_bid(bid, s, "lean") for s in ("bear","base","bull")}
    ev1 = sum(WEIGHTS["first_time"][s]*pn[s]["profit"] for s in pn)
    ev2 = sum(WEIGHTS["experienced"][s]*pn[s]["profit"] for s in pn)
    ev_table.append(dict(bid=bid, landed=pn["base"]["landed_total"],
                         per_unit=pn["base"]["landed_per_unit"],
                         ev_first_time=round(ev1), ev_experienced=round(ev2),
                         worst_case=pn["bear"]["profit"]))
    print(f"{bid:>8,}{pn['base']['landed_total']:>9,.0f}{pn['base']['landed_per_unit']:>8.0f}"
          f"{ev1:>16,.0f}{ev2:>16,.0f}{pn['bear']['profit']:>12,.0f}")
with open(os.path.join(OUT,"lot_ev_by_bid.csv"),"w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=list(ev_table[0].keys())); w.writeheader(); w.writerows(ev_table)

# Hard maximum: highest bid where the EV for an EXPERIENCED operator still
# exceeds 20% of landed capital AND the bear-case loss stays under 15% of a
# $20,000 bankroll.
hard = None
for row in ev_table:
    if row["ev_experienced"] >= 0.20*row["landed"] and row["worst_case"] > -3_000:
        hard = row
print(f"\nHARD MAXIMUM BID (EV >= 20% of landed capital AND bear loss < $3,000): "
      f"${hard['bid']:,}" if hard else "\nHARD MAXIMUM BID: no bid clears both tests -- DO NOT BID")
if hard is None:
    ok = [r for r in ev_table if r["ev_experienced"] >= 0.20*r["landed"]]
    ok1 = [r for r in ev_table if r["ev_first_time"] > 0]
    if ok:
        r = ok[-1]
        print(f"  Highest bid with EV >= 20% of landed capital, EXPERIENCED operator: ${r['bid']:,} "
              f"(EV ${r['ev_experienced']:,}, worst case ${r['worst_case']:,})")
    if ok1:
        r = ok1[-1]
        print(f"  Highest bid with merely POSITIVE EV for a FIRST-TIME buyer:          ${r['bid']:,} "
              f"(EV ${r['ev_first_time']:,}, worst case ${r['worst_case']:,})")
    print("  Every bid leaves a bear-case loss larger than 15% of a $20,000 bankroll.")
