# PART 10 — STAFFING

## Michigan wage basis (verified)

BLS, **Detroit–Warren–Dearborn MSA, May 2025**: all-occupation mean hourly wage **$33.27**
(national $33.54). Grand Rapids $29.16. National median for hand laborers and material movers:
**$38,220/yr**.

Appliance-industry roles sit **below** the MSA mean. Rates used, with a **1.28× burden** for
FICA, workers' compensation, unemployment insurance and general liability:

| Role | Base hourly | Base annual | **Fully loaded monthly** |
|---|---:|---:|---:|
| Warehouse / receiving / test / clean | $20.00 | $41,600 | **$4,437** |
| Sales associate (+ commission) | $18.75 | $39,000 | **$4,160** |
| Customer service rep | $16.88 | $35,100 | **$3,744** |
| Delivery driver | $21.00 | $43,680 | **$4,659** |
| Delivery helper | $17.02 | $35,400 | **$3,776** |
| **Appliance repair technician** | $28.00 | $58,240 | **$6,212** |
| Operations manager | $31.25 | $65,000 | **$6,917** |
| **Blended FTE used in the model** | | | **$4,600** |

**[ESTIMATE]** — BLS publishes the MSA mean and the national laborer median; the per-role
Detroit splits are my derivations from those anchors and are the weakest inputs in this part.

## Productivity standard

From `models/labor_productivity.py`: **99 minutes = 1.65 hours per unit**, delivery excluded
(receive, test, clean, photograph, list, stage, sell, repair-amortised, manage-amortised). At
168 hours/month:

| Effectiveness | Units per FTE per month |
|---|---:|
| Conservative (72%) | **73** |
| **Base (80%)** | **81** |
| Optimistic (88%) | **90** |

Cross-check: press reporting on a Kentucky operator describes **200 appliances sold in one
month** by a very small operation **[ANECDOTAL]**. That is consistent with 2–2.5 FTE at this
standard, or with one person working 70-hour weeks and skipping deep cleaning and testing.

Delivery, if in-house: 2-person crew, 10 stops/day, 21 days = **210 deliveries/crew/month**.

## Staffing by volume

Owner counts as 1.5 FTE in year one and 1.0 thereafter. Delivery is **outsourced** (Part 8) up
to 250 units/month.

| Units/mo | Trucks/mo | FTE needed | Owner covers | **Paid FTE** | Composition | **Monthly payroll** | Payroll per unit |
|---:|---:|---:|---:|---:|---|---:|---:|
| **50** | 1.1 | 0.6 | 1.5 | **0** | Owner only | **$0** | $0 |
| **100** | 2.1 | 1.2 | 1.5 | **0** | Owner only | **$0** | $0 |
| **150** | 3.2 | 1.9 | 1.0 | **0.9** | 1 warehouse/sales generalist | **$4,140** | $28 |
| **250** | 5.3 | 3.1 | 1.0 | **3.1** | 2 warehouse, 1 sales, **+1 repair tech** | **$16,072** | $64 |
| **350** | 7.4 | 4.3 | 1.0 | **5.3** | 3 warehouse, 1.5 sales, 1 tech, **+1 manager**, +1.5 second-site | **$26,489** | $76 |
| **500** | 10.6 | 6.2 | 1.0 | **8.2** | 4 warehouse, 2 sales, 1 CSR, 1 tech, 1 manager, +3.0 satellite sites | **$39,820** | $80 |

## The step-function problem

Payroll per unit goes **$0 → $28 → $64 → $76 → $80** as you scale. Contribution per unit is
**$126.50** and does not move. Add rent (roughly $25–$35/unit at these volumes) and:

| Units/mo | Contribution/unit | Payroll/unit | Rent/unit | **Left over** |
|---:|---:|---:|---:|---:|
| 100 | $126.50 | $0 | $27 | **$99.50** |
| 150 | $126.50 | $28 | $30 | **$68.50** |
| 250 | $126.50 | $64 | $34 | **$28.50** |
| 350 | $126.50 | $76 | $32 | **$18.50** |
| 500 | $126.50 | $80 | $33 | **$13.50** |

**Every employee you hire destroys about a third of your remaining margin per unit, and the
volume they enable does not replace it.** That is the arithmetic behind Part 2's observation
that the reliably profitable operators in this industry are the ones with no employees, and
behind the peak-then-decline profit curve in Part 11.

**The first hire is the single most consequential decision in the business.** At $4,600 fully
loaded, that person must generate **37 incremental units per month** just to pay for
themselves — nearly a full truck. If they generate 81 units (the standard), they contribute
$10,247 of contribution against $4,600 of cost, which works. If they generate 50, they lose
you money. **Hire only when you are personally turning away sales, and hire someone who can
both process and sell.**

## Michigan compliance triggers

- **Workers' compensation is required from the first employee.** No small-team exemption.
- Unemployment insurance registration, wage-and-hour compliance, I-9s.
- If your delivery crew are employees, **commercial auto** at $1,800–$3,500/vehicle/yr and
  driver-qualification screening.
- **EPA Section 608 certification** is required for anyone opening a sealed refrigerant system
  — including recovering refrigerant from a scrap refrigerator (Part 17).

## Recommendation

**Stay at zero paid employees through 150 units/month.** That configuration produces roughly
$7,500/month of operating profit and is the highest-margin state the business ever reaches.

When you do hire, hire **one generalist** who can receive, test, clean, photograph and close a
sale — not a specialist. The repair technician at $6,212/month is only justified past ~200
units/month; below that, subcontract repairs or scrap the unit.

---

*Sources: [`research/SOURCES.md`](research/SOURCES.md). Model: `models/labor_productivity.py`,
`models/steady_state.py`.*
