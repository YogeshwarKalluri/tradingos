"""Bottom-up labor standard. This single number drives the whole model, so it is
derived from task times rather than assumed."""
TASKS = [
 # task,                                          minutes per unit handled
 ("Receive / hand-unload floor-loaded truck",      6),
 ("Inspect, function-test, record condition",     14),
 ("Deep clean, touch-up, polish",                 16),
 ("Photograph (8-12 shots) + write listing",      12),
 ("Move/stage in warehouse, label, inventory",     6),
 ("Customer service: FB/OfferUp msgs, calls",     14),
 ("Showroom selling, close, paperwork, payment",  11),
 ("Repair work, amortised (12% x ~90 min)",       11),
 ("Management, buying, admin, bookkeeping, amort", 9),
]
PROD_MIN = sum(t[1] for t in TASKS)
HRS_MONTH = 168          # 21 working days x 8 hrs
EFFICIENCY = {"conservative":0.72, "base":0.80, "optimistic":0.88}  # non-productive time
print("TASK STANDARD (minutes per unit, delivery EXCLUDED - assumed outsourced):")
for t,m in TASKS: print(f"  {t:<48}{m:>4}")
print(f"  {'TOTAL':<48}{PROD_MIN:>4} min/unit = {PROD_MIN/60:.2f} hrs/unit\n")
for k,e in EFFICIENCY.items():
    upf = HRS_MONTH*e/(PROD_MIN/60)
    print(f"  {k:<13} {e:.0%} effective -> {upf:5.1f} units per FTE per month")
print("\nDELIVERY (if brought in-house): 2-person crew, 10 stops/day, 21 days")
print("  = 210 deliveries/crew/month; at 45% attach that supports ~466 units/month/crew")
