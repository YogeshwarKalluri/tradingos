"""Monte Carlo over the 36-month model's key drivers.
Distributions are centred on the base case with spreads set by how much each
driver is observed to vary in the sourced data (see research/SOURCES.md)."""
import random, statistics, json, os, importlib.util, math, io, contextlib
random.seed(20260908)
spec = importlib.util.spec_from_file_location("bm", os.path.join(os.path.dirname(__file__),"business_model_36mo.py"))
with contextlib.redirect_stdout(io.StringIO()):
    bm = importlib.util.module_from_spec(spec); spec.loader.exec_module(bm)

BASE = dict(bm.S["base"])
N = 4000

def tri(lo, mode, hi): return random.triangular(lo, hi, mode)

def draw():
    p = dict(BASE)
    # Landed cost/unit. Observed B-Stock Lowe's S&D clearing: $188-245/unit bid,
    # plus ~10% premium plus freight -> $230-290 landed at MARKET price.
    # $150-175 is only reachable with real buying discipline and short freight.
    p["landed_unit"]   = tri(145, 178, 250)
    p["merch_rev"]     = tri(300, 355, 400)
    p["anc_rev"]       = tri(30,  60,  92)
    p["var_purchase"]  = tri(38,  51,  74)
    p["var_sold"]      = tri(52,  67,  92)
    p["units_per_fte"] = tri(66,  81,  94)
    p["demand_start"]  = tri(11,  21,  33)
    p["demand_growth"] = tri(0.055,0.105,0.16)
    p["demand_ceiling"]= tri(170, 300, 520)
    p["loc_ceiling"]   = tri(150, 215, 290)
    p["source_start"]  = tri(45,  88,  150)
    p["dead_after"]    = 6
    p["sell_curve"]    = [tri(0.30,0.44,0.56), 0.26, 0.14, 0.05, 0.02]
    p["max_locations"] = random.choice([1,2,2,3])
    p["credit_line"]   = random.choice([0, 25_000, 50_000, 75_000, 150_000])
    return p

res=[]
for i in range(N):
    bm.S["mc"] = draw()
    with contextlib.redirect_stdout(io.StringIO()):
        rows, ms, _ = bm.run("mc")
    res.append(dict(cum=rows[-1]["cum_profit"], cum_ao=rows[-1]["cum_profit_after_owner"],
                    y3rev=sum(r["revenue"] for r in rows[24:36]),
                    m36=rows[-1]["units_sold"], ms=ms,
                    insolvent=any(r.get("insolvent") for r in rows),
                    maxdebt=max(r["debt_drawn"] for r in rows)))

def pct(f): return 100*sum(1 for r in res if f(r))/len(res)
cums=sorted(r["cum"] for r in res); caos=sorted(r["cum_ao"] for r in res)
q=lambda a,pp: a[int(pp*(len(a)-1))]

print(f"MONTE CARLO  n={N}  36-month cumulative OPERATING profit (before owner pay)")
print(f"  P5  ${q(cums,0.05):>10,.0f}   P25 ${q(cums,0.25):>10,.0f}   MEDIAN ${q(cums,0.50):>10,.0f}"
      f"   P75 ${q(cums,0.75):>10,.0f}   P95 ${q(cums,0.95):>10,.0f}")
print(f"  mean ${statistics.mean(cums):,.0f}")
print(f"\n36-month cumulative profit AFTER a market-rate owner salary")
print(f"  P5  ${q(caos,0.05):>10,.0f}   P25 ${q(caos,0.25):>10,.0f}   MEDIAN ${q(caos,0.50):>10,.0f}"
      f"   P75 ${q(caos,0.75):>10,.0f}   P95 ${q(caos,0.95):>10,.0f}")
print("\nPROBABILITY OF REACHING CUMULATIVE PROFIT WITHIN 36 MONTHS")
print(f"{'target':>12}{'before owner pay':>20}{'after owner pay':>18}")
for lvl in (0,100_000,250_000,500_000,750_000,1_000_000,2_000_000):
    print(f"{lvl:>12,}{pct(lambda r,l=lvl: r['cum']>=l):>19.1f}%{pct(lambda r,l=lvl: r['cum_ao']>=l):>17.1f}%")
print(f"\nP(business is insolvent / dead at some point) : {pct(lambda r: r['insolvent']):.1f}%")
print(f"P(loses money over 36 months, before owner pay): {pct(lambda r: r['cum']<0):.1f}%")
print(f"P(owner earns less than $4,500/mo equivalent)  : {pct(lambda r: r['cum']<162_000):.1f}%")
med_month = [r["ms"].get(1_000_000) for r in res if 1_000_000 in r["ms"]]
print(f"Of runs that DO clear $1M, median month reached : "
      f"{statistics.median(med_month) if med_month else 'n/a'}  (n={len(med_month)})")
json.dump(dict(n=N, p5=q(cums,.05), p25=q(cums,.25), median=q(cums,.5), p75=q(cums,.75),
    p95=q(cums,.95), mean=statistics.mean(cums),
    probs={str(l): dict(before=pct(lambda r,x=l: r['cum']>=x), after=pct(lambda r,x=l: r['cum_ao']>=x))
           for l in (0,100_000,250_000,500_000,750_000,1_000_000,2_000_000)},
    p_insolvent=pct(lambda r: r['insolvent']), p_loss=pct(lambda r: r['cum']<0)),
    open(os.path.join(os.path.dirname(__file__),"outputs","monte_carlo.json"),"w"), indent=2)
