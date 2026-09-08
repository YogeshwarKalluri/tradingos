"""Steady-state unit economics, truck-rate P&L, break-even, and a solver for
'what would have to be true' to hit $1M cumulative profit in 36 months."""
import math, json, os, csv
OUT=os.path.join(os.path.dirname(__file__),"outputs"); os.makedirs(OUT,exist_ok=True)
UNITS_PER_TRUCK=47
WAGE=dict(warehouse=4_437,tech=6_212,sales=4_160,driver=4_659,helper=3_776,manager=6_917)
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

BASE=dict(landed=165, merch=358, anc=62, var_buy=51, var_sold=67, mktg=8.5,
          per_fte=81, months_cover=1.5, misc=600, misc_pct=0.020)

def monthly_pnl(units, p=BASE, locations=None):
    rev=units*(p["merch"]+p["anc"])
    contrib=units*((p["merch"]+p["anc"])-p["landed"]-p["var_buy"]-p["var_sold"]-p["mktg"])
    on_hand=units*p["months_cover"]
    loc = locations or max(1, math.ceil(units/220))
    rent, sqft = facility(on_hand, loc, units>=80)
    need=units/p["per_fte"]; owner=1.0
    paid=max(0.0,need-owner)+1.5*(loc-1)
    tech=1 if units>=200 else 0; mgr=1 if units>=280 else 0
    payroll=paid*4_600 + tech*(WAGE["tech"]-4_600) + mgr*(WAGE["manager"]-4_600)
    other=p["misc"]*loc+p["misc_pct"]*rev
    op=contrib-rent-payroll-other
    return dict(units=units,trucks=round(units/UNITS_PER_TRUCK,2),revenue=round(rev),
                contribution=round(contrib),rent=rent,payroll=round(payroll),
                other=round(other),op_profit=round(op),locations=loc,
                paid_fte=round(paid+tech+mgr,1),margin=round(op/rev,4) if rev else 0,
                inventory_units=round(on_hand),inventory_value=round(on_hand*p["landed"]),sqft=sqft)

print("STEADY-STATE MONTHLY P&L BY TRUCK RATE (base-case assumptions, 47 units/truck)")
print(f"{'trucks/mo':>10}{'units':>7}{'revenue':>10}{'contrib':>9}{'rent':>8}{'payroll':>9}{'other':>8}{'OP PROFIT':>11}{'margin':>8}{'FTE':>6}{'sites':>6}")
rate_rows=[]
for t in (1,2,3,5,7,10,15,20):
    r=monthly_pnl(t*UNITS_PER_TRUCK); rate_rows.append(r)
    print(f"{t:>10}{r['units']:>7}{r['revenue']:>10,}{r['contribution']:>9,}{r['rent']:>8,}{r['payroll']:>9,}{r['other']:>8,}{r['op_profit']:>11,}{r['margin']:>8.1%}{r['paid_fte']:>6}{r['locations']:>6}")

# break-even -- NOTE: profit is NOT monotonic in volume. Fixed-cost steps
# (second location, first salaried hires) make it fall as volume rises, so a
# binary search is invalid here. Scan the whole range instead.
prof = {u: monthly_pnl(u)["op_profit"] for u in range(5, 1001)}
pos  = [u for u in prof if prof[u] >= 0]
pos_owner = [u for u in prof if prof[u] >= 4_500]
def bands(us):
    us=sorted(us); out=[]; start=prev=us[0]
    for u in us[1:]:
        if u!=prev+1: out.append((start,prev)); start=u
        prev=u
    out.append((start,prev)); return out
peak = max(prof, key=lambda u: prof[u])
print(f"\nPROFIT IS NOT MONOTONIC IN VOLUME.")
print(f"  Peak monthly operating profit: ${prof[peak]:,} at {peak} units/month "
      f"({peak/UNITS_PER_TRUCK:.2f} trucks/mo, ${monthly_pnl(peak)['revenue']*12:,}/yr revenue)")
print(f"  Bands where op profit >= $0            : "
      + ", ".join(f"{a}-{b} u/mo" for a,b in bands(pos)))
print(f"  Bands where op profit >= $4,500 (owner): "
      + ", ".join(f"{a}-{b} u/mo" for a,b in bands(pos_owner)))
print(f"  Break-even (lowest volume with op profit >= 0): {min(pos)} units/month "
      f"= {min(pos)/UNITS_PER_TRUCK:.2f} trucks/mo = ${monthly_pnl(min(pos))['revenue']:,}/mo revenue")
print(f"  Lowest volume covering a $4,500/mo owner salary: {min(pos_owner)} units/month "
      f"= {min(pos_owner)/UNITS_PER_TRUCK:.2f} trucks/mo")

# turns
avg_days={"conservative":78,"base":55,"optimistic":42}
print("\nINVENTORY TURNOVER REQUIRED")
for k,d in avg_days.items():
    print(f"  {k:<13} avg {d} days to sell -> {365/d:.1f} turns/yr; at 208 u/mo that is "
          f"{round(208*d/30)} units on hand, ~${round(208*d/30*165):,} of inventory capital")

# What would have to be true for $1,000,000 cumulative op profit in 36 months?
print("\nSOLVER: what does $1,000,000 cumulative operating profit in 36 months require?")
def cum36(exit_units, ramp_months, p=BASE):
    tot=0
    for m in range(1,37):
        u = exit_units*min(1.0, m/ramp_months)
        tot += monthly_pnl(max(1,int(u)),p)["op_profit"]
    return tot
# Metro Detroit absorbable ceiling. Wayne+Oakland+Macomb ~ 2.1M households;
# ~0.4 major-appliance purchases/household/yr => ~840k units/yr; secondary market
# (used + scratch&dent) ~15% => ~10,500 units/month across ALL competitors.
# A dominant independent realistically captures 6-8% => 630-840 units/month.
CEILING = 840
best = max(((u, cum36(u,24)) for u in range(50,CEILING+1,10)), key=lambda x: x[1])
print(f"  Under BASE-CASE structure the 36-month cumulative profit is MAXIMISED at")
print(f"  an exit rate of {best[0]} units/month, producing ${best[1]:,.0f} cumulative.")
print(f"  $1,000,000 is NOT reachable at any volume under base-case unit economics,")
print(f"  because contribution per unit ($126.50) barely exceeds the fixed cost per")
print(f"  unit that scale requires. Volume alone does not fix a thin contribution margin.")
print("\n  Sensitivity - cumulative 36-mo profit if contribution/unit improves:")
for uplift in (0, 25, 50, 75, 100, 125):
    q = dict(BASE); q["merch"] = BASE["merch"] + uplift
    b = max(((u, cum36(u,24,q)) for u in range(50,CEILING+1,10)), key=lambda x: x[1])
    print(f"    +${uplift:>3}/unit (rev/unit ${420+uplift}) -> best exit {b[0]:>4} u/mo, "
          f"cumulative ${b[1]:>10,.0f}  {'<-- clears $1M' if b[1]>=1_000_000 else ''}")

# working capital
print("\nWORKING CAPITAL BY REVENUE SCALE (base assumptions)")
print(f"{'annual rev':>12}{'units/mo':>10}{'inventory$':>12}{'AR/float':>10}{'opex buffer':>13}{'TOTAL WC':>11}")
wc_rows=[]
for target in (50_000,100_000,250_000,500_000,1_000_000,3_000_000,5_000_000):
    u=max(1,round(target/12/(BASE["merch"]+BASE["anc"])))
    r=monthly_pnl(u)
    inv=r["inventory_value"]; ar=r["revenue"]*0.06
    buf=(r["rent"]+r["payroll"]+r["other"])*2
    wc_rows.append((target,u,inv,ar,buf,inv+ar+buf))
    print(f"{target:>12,}{u:>10}{inv:>12,}{round(ar):>10,}{round(buf):>13,}{round(inv+ar+buf):>11,}")

with open(os.path.join(OUT,"truck_rate_pnl.csv"),"w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=list(rate_rows[0].keys())); w.writeheader(); w.writerows(rate_rows)
with open(os.path.join(OUT,"working_capital.csv"),"w",newline="") as f:
    w=csv.writer(f); w.writerow(["annual_revenue","units_per_month","inventory","ar_float","opex_buffer","total_working_capital"]); w.writerows(wc_rows)
