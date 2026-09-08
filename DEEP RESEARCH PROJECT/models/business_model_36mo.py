"""
36-month month-by-month model, $20,000 starting capital, Metro Detroit.

Structure: contribution per unit is thin, so the model's real job is to show
where FIXED COST steps (lease, payroll) outrun DEMAND. Facility and headcount
scale with actual volume rather than being assumed.

Profit reported BEFORE and AFTER a market-rate owner salary. They are different
things and are never mixed.
"""
import math, csv, json, os
OUT = os.path.join(os.path.dirname(__file__), "outputs"); os.makedirs(OUT, exist_ok=True)
START_CASH, MONTHS = 20_000, 36

# Fully-loaded monthly cost per FTE (Michigan wage x 1.28 payroll burden)
BLENDED_FTE_COST = 4_600   # weighted mix of warehouse/sales/CSR, fully loaded
WAGE = dict(warehouse=4_437, tech=6_212, sales=4_160, driver=4_659, helper=3_776,
            csr=3_744, manager=6_917)

SQFT_PER_UNIT = 14          # appliance footprint stacked 2-high incl. aisles
SHOWROOM_SQFT = 1_800       # per retail location
def facility(on_hand, locations=1, showroom=True):
    """SE Michigan all-in occupancy cost. Asking rents: Livonia $8.20-8.66/sf,
    Sterling Heights $9.45-9.93/sf, Detroit avg $9.66/sf (NNN). Grossed up ~$3/sf
    for CAM, taxes, insurance, utilities. Small units carry a size premium."""
    # Below ~80 units/month there is no showroom: appointment-only from a small
    # flex unit or pole barn, selling through Facebook Marketplace. This is how
    # every bootstrapped operator actually starts, and it changes the answer.
    sqft = max(600, on_hand*SQFT_PER_UNIT + (SHOWROOM_SQFT*locations if showroom else 0))
    psf_yr = 16.0 if sqft < 2_500 else (13.5 if sqft < 5_000 else 12.0)
    return round(sqft*psf_yr/12), round(sqft)

S = {
"conservative": dict(
    landed_unit=195, merch_rev=330, anc_rev=44,
    var_purchase=62, var_sold=76, marketing_unit=11.0, salvage=45,
    sell_curve=[0.32,0.24,0.14,0.08,0.05], dead_after=6,
    demand_start=15, demand_growth=0.075, demand_ceiling=185,
    source_start=55, source_growth=5, source_ceiling=220,
    units_per_fte=73, delivery_attach=0.38,
    owner_salary=3_500, credit_line=0, apr=0.0, misc_base=520, misc_scale=0.022,
    loc_ceiling=150, max_locations=1),
"base": dict(
    landed_unit=165, merch_rev=358, anc_rev=62,
    var_purchase=51, var_sold=67, marketing_unit=8.5, salvage=60,
    sell_curve=[0.45,0.27,0.14,0.05,0.02], dead_after=6,
    demand_start=22, demand_growth=0.11, demand_ceiling=330,
    source_start=90, source_growth=12, source_ceiling=500,
    units_per_fte=81, delivery_attach=0.45,
    owner_salary=4_500, credit_line=75_000, apr=0.13, misc_base=600, misc_scale=0.020,
    loc_ceiling=220, max_locations=2),
"optimistic": dict(
    landed_unit=158, merch_rev=380, anc_rev=78,
    var_purchase=44, var_sold=58, marketing_unit=7.0, salvage=75,
    sell_curve=[0.55,0.26,0.11,0.04,0.02], dead_after=6,
    demand_start=30, demand_growth=0.145, demand_ceiling=600,
    source_start=140, source_growth=22, source_ceiling=950,
    units_per_fte=90, delivery_attach=0.55,
    owner_salary=6_000, credit_line=250_000, apr=0.115, misc_base=750, misc_scale=0.018,
    loc_ceiling=300, max_locations=3),
}
CASH_FLOOR = 2_500

def run(name):
    p = S[name]; cash = float(START_CASH); drawn = 0.0
    buckets = []; rows = []; cum = 0.0; cum_ao = 0.0; ms = {}; locations = 1; ceased = None
    for m in range(1, MONTHS+1):
        # A rational owner closes rather than paying rent on an empty building.
        # Shut down when three straight losing months coincide with no ability to
        # restock. One month of wind-down cost (lease break / disposal) is booked.
        if ceased is None and len(rows) >= 3:
            on_h = sum(b[0] for b in buckets)
            broke = cash < (rows[-1]["rent"] + rows[-1]["other_fixed"])
            if all(r["op_profit"] < 0 for r in rows[-3:]) and broke and on_h < 20:
                ceased = m
                emitted_cease_month = m
                winddown = rows[-1]["rent"] + rows[-1]["other_fixed"]
                cum -= winddown; cum_ao -= winddown; cash -= winddown
                rows.append(dict(rows[-1], month=m, trucks=0, units_purchased=0, units_sold=0,
                    salvaged=0, revenue=0, cogs_incl_freight=0, repairs_processing=0,
                    marketing=0, payroll=0, rent=0, other_fixed=round(winddown), interest=0,
                    op_profit=round(-winddown), owner_salary=0, profit_after_owner=round(-winddown),
                    cum_profit=round(cum), cum_profit_after_owner=round(cum_ao), cash=round(cash),
                    inventory_units=0, inventory_value=0, insolvent="CEASED OPERATIONS"))
        if ceased is not None:
            if m == emitted_cease_month:
                continue                       # wind-down row already written
            if len(rows) < MONTHS:
                rows.append(dict(rows[-1], month=m, revenue=0, op_profit=0, owner_salary=0,
                    profit_after_owner=0, units_purchased=0, units_sold=0, salvaged=0,
                    rent=0, payroll=0, other_fixed=0, marketing=0, repairs_processing=0,
                    cogs_incl_freight=0, interest=0, inventory_units=0, inventory_value=0,
                    cum_profit=round(cum), cum_profit_after_owner=round(cum_ao), cash=round(cash)))
            continue
        demand_cap = min(p["demand_ceiling"], p["demand_start"]*((1+p["demand_growth"])**(m-1)))
        # A second/third storefront is opened only when demand is genuinely capped
        # AND the trailing 3-month profit run-rate can absorb the new fixed cost.
        # An operator who opens a site he cannot fund simply goes broke, so the
        # model refuses to do it for him.
        if locations < p["max_locations"] and len(rows) >= 3:
            capped = all(r["units_sold"] >= 0.93*locations*p["loc_ceiling"] for r in rows[-3:])
            t3 = sum(r["op_profit"] for r in rows[-3:])/3
            new_site_cost = facility(p["loc_ceiling"]*1.5,1)[0] + 1.5*4_600 + p["misc_base"]
            if capped and t3 > 1.5*new_site_cost:
                locations += 1
        demand_cap = min(demand_cap, locations*p["loc_ceiling"])
        source_cap = min(p["source_ceiling"], p["source_start"] + p["source_growth"]*m)
        on_hand = sum(b[0] for b in buckets)
        prior_sold = rows[-1]["units_sold"] if rows else 0
        prior_buy  = rows[-1]["units_purchased"] if rows else 0

        # ---- facility & headcount sized to actual recent volume ----------
        showroom = max(on_hand, prior_buy) >= 80
        rent, sqft = facility(max(on_hand, prior_buy*1.2), locations, showroom)
        facil = f"{locations} site(s), {sqft:,} sqft total"
        extra_site_fte = 1.5*(locations-1)   # each satellite needs its own floor crew
        # Blended all-in productivity: receive/test/clean/photo/list/sell/deliver.
        # Anchored to observed one- and two-person operators moving ~100 units/person/mo.
        owner_fte = 1.5 if m <= 12 else 1.0         # owner works the floor, unpaid in Y1
        throughput = max(prior_buy, prior_sold)
        need_fte = throughput / p["units_per_fte"]
        paid_fte = max(0.0, need_fte - owner_fte) + extra_site_fte
        tech = 1 if throughput >= 200 else 0        # dedicated repair tech (skill premium)
        mgr  = 1 if throughput >= 280 else 0        # ops manager once owner is spread thin
        # role mix of paid_fte: 45% warehouse, 30% sales/CSR, 25% driver/helper
        payroll = paid_fte*BLENDED_FTE_COST + tech*(WAGE["tech"]-BLENDED_FTE_COST if tech else 0) \
                  + mgr*(WAGE["manager"]-BLENDED_FTE_COST if mgr else 0)

        # ---- purchasing: min(cash, sourcing supply, forward demand cover) --
        prior_rev = rows[-1]["revenue"] if rows else 0
        fixed_est = payroll + rent + p["misc_base"]*locations + p["misc_scale"]*prior_rev
        avail = max(0.0, cash - max(CASH_FLOOR, fixed_est*0.9))
        cover_gap = max(0.0, demand_cap*2.0 - on_hand)
        buy = min(avail/p["landed_unit"], source_cap, cover_gap)
        if p["credit_line"] > 0 and m >= 12 and cum > 0:
            want_more = min(source_cap, cover_gap) - buy
            headroom = p["credit_line"] - drawn
            if want_more > 0 and headroom > 0:
                take = min(headroom, want_more*p["landed_unit"]); drawn += take; cash += take
                avail = max(0.0, cash - max(CASH_FLOOR, fixed_est*0.9))
                buy = min(avail/p["landed_unit"], source_cap, cover_gap)
        buy = int(max(0, math.floor(buy)))
        cash -= buy*p["landed_unit"]
        buckets.append([buy, 0])

        # ---- selling ------------------------------------------------------
        want = 0.0
        for b in buckets:
            i = b[1]
            if i < len(p["sell_curve"]):
                remaining_share = 1 - sum(p["sell_curve"][:i])
                want += b[0]*p["sell_curve"][i]/max(1e-9, remaining_share)
        want = min(want, sum(b[0] for b in buckets))
        sold = min(want, demand_cap)
        need = sold
        for b in sorted(buckets, key=lambda x: -x[1]):
            t = min(b[0], need); b[0] -= t; need -= t
            if need <= 1e-9: break
        sold -= need

        salv = 0
        for b in buckets: b[1] += 1
        for b in buckets:
            if b[1] > p["dead_after"] and b[0] > 0: salv += b[0]; b[0] = 0
        buckets = [b for b in buckets if b[0] > 0.001]

        # ---- P&L -----------------------------------------------------------
        revenue = sold*(p["merch_rev"]+p["anc_rev"]) + salv*p["salvage"]
        cogs    = (sold+salv)*p["landed_unit"]
        varc    = buy*p["var_purchase"] + sold*p["var_sold"]
        mktg    = buy*p["marketing_unit"]
        other   = p["misc_base"]*locations + p["misc_scale"]*revenue
        interest= drawn*p["apr"]/12
        op = revenue - cogs - varc - mktg - payroll - rent - other - interest
        osal = p["owner_salary"] if m > 12 else 0
        cum += op; cum_ao += op - osal
        cash += revenue - varc - mktg - payroll - rent - other - interest - osal
        oh = sum(b[0] for b in buckets)
        for lvl in (250_000,500_000,750_000,1_000_000,1_500_000,2_000_000):
            if cum >= lvl and lvl not in ms: ms[lvl] = m
        rows.append(dict(month=m, trucks=round(buy/47,2), units_purchased=buy,
            units_sold=int(round(sold)), salvaged=int(round(salv)), revenue=round(revenue),
            cogs_incl_freight=round(cogs), repairs_processing=round(varc), marketing=round(mktg),
            payroll=round(payroll), rent=rent, other_fixed=round(other), interest=round(interest),
            op_profit=round(op), owner_salary=osal, profit_after_owner=round(op-osal),
            cum_profit=round(cum), cum_profit_after_owner=round(cum_ao), cash=round(cash),
            inventory_units=int(round(oh)), inventory_value=round(oh*p["landed_unit"]),
            debt_drawn=round(drawn), facility=facil, sqft=sqft, locations=locations, showroom=int(showroom),
            paid_fte=round(paid_fte+tech+mgr,1), total_fte=round(paid_fte+tech+mgr+owner_fte,1),
            insolvent=""))
        if cash < -1_000 and drawn >= p["credit_line"]:
            rows[-1]["insolvent"] = "INSOLVENT"
            break
    return rows, ms, p

summary={}
for name in S:
    rows, ms, p = run(name)
    with open(os.path.join(OUT,f"model_{name}.csv"),"w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    y=lambda a,b,k: sum(r[k] for r in rows[a:b])
    summary[name]=dict(y1_rev=y(0,12,"revenue"),y2_rev=y(12,24,"revenue"),y3_rev=y(24,36,"revenue"),
        y1_profit=y(0,12,"op_profit"),y2_profit=y(12,24,"op_profit"),y3_profit=y(24,36,"op_profit"),
        y1_profit_ao=y(0,12,"profit_after_owner"),y2_profit_ao=y(12,24,"profit_after_owner"),
        y3_profit_ao=y(24,36,"profit_after_owner"),
        cum36=rows[-1]["cum_profit"],cum36_ao=rows[-1]["cum_profit_after_owner"],
        peak_headcount=max(r["total_fte"] for r in rows),m36_sold=rows[-1]["units_sold"],
        m36_bought=rows[-1]["units_purchased"],m36_trucks=rows[-1]["trucks"],
        m36_facility=rows[-1]["facility"],max_debt=max(r["debt_drawn"] for r in rows),
        min_cash=min(r["cash"] for r in rows),peak_inv_value=max(r["inventory_value"] for r in rows),
        peak_wc=max(r["inventory_value"]+max(0,r["cash"]) for r in rows),
        milestones={str(k):v for k,v in ms.items()})
    print(f"\n=== {name.upper()} ===")
    for lbl,a,b in (("Y1",0,12),("Y2",12,24),("Y3",24,36)):
        print(f"  {lbl}: rev ${y(a,b,'revenue'):>10,.0f} | op profit ${y(a,b,'op_profit'):>9,.0f} | after owner pay ${y(a,b,'profit_after_owner'):>9,.0f}")
    print(f"  36-mo cumulative operating profit          : ${rows[-1]['cum_profit']:>10,.0f}")
    print(f"  36-mo cumulative after market owner salary : ${rows[-1]['cum_profit_after_owner']:>10,.0f}")
    print(f"  Month 36: bought {rows[-1]['units_purchased']}u ({rows[-1]['trucks']} trucks) / sold {rows[-1]['units_sold']}u | "
          f"{rows[-1]['total_fte']} FTE | {rows[-1]['facility']} | debt ${rows[-1]['debt_drawn']:,.0f}")
    print(f"  Peak inventory value ${max(r['inventory_value'] for r in rows):,.0f} | min cash ${min(r['cash'] for r in rows):,.0f}")
    print(f"  Milestones (cum op profit -> month): {ms if ms else 'NONE reached in 36 months'}")
with open(os.path.join(OUT,"scenario_summary.json"),"w") as f: json.dump(summary,f,indent=2)
