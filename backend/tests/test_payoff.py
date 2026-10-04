"""
Validation suite for the payoff engine.

Every expected value here is either textbook-documented or derivable
by hand. If the engine passes these, the maths is right and nothing
is being special-cased.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.payoff import (  # noqa: E402
    Direction,
    Leg,
    OptionType,
    analyse,
    breakevens,
    max_loss,
    max_profit,
    payoff,
    payoff_curve,
    payoff_lots,
)

CALL = OptionType.CALL
PUT = OptionType.PUT
BUY = Direction.BUY
SELL = Direction.SELL

failures: list[str] = []
checks = 0


def check(name: str, actual, expected, tol: float = 1e-6) -> None:
    global checks
    checks += 1
    if isinstance(expected, float) and math.isinf(expected):
        ok = math.isinf(actual) and (actual > 0) == (expected > 0)
    elif isinstance(expected, list):
        ok = len(actual) == len(expected) and all(
            abs(a - b) < tol
            if isinstance(a, (int, float)) and isinstance(b, (int, float))
            else a == b
            for a, b in zip(actual, expected)
        )
    elif isinstance(expected, float):
        ok = abs(actual - expected) < tol
    else:
        ok = actual == expected
    if not ok:
        failures.append(f"{name}: got {actual!r}, expected {expected!r}")
        print(f"  FAIL  {name}\n        got {actual!r}  expected {expected!r}")
    else:
        print(f"  ok    {name}")


# --------------------------------------------------------------- long call
# buy 2000 C @ 100  ->  max loss 100, BE 2100, unlimited upside
legs = [Leg(CALL, BUY, 2000, 100)]
check("long call @2000: payoff at strike", payoff(legs, 2000), -100.0)
check("long call @2000: payoff at 2200", payoff(legs, 2200), 100.0)
check("long call @2000: payoff at 1800", payoff(legs, 1800), -100.0)
check("long call @2000: max loss", max_loss(legs), -100.0)
check("long call @2000: max profit", max_profit(legs), math.inf)
check("long call @2000: breakeven", breakevens(legs), [2100.0])
check("long call @2000: lot P&L at 2200", payoff_lots(legs, 2200), 10000.0)

# ----------------------------------------------------------------- long put
# buy 2000 P @ 100  ->  max loss 100, BE 1900, unlimited downside
legs = [Leg(PUT, BUY, 2000, 100)]
check("long put @2000: payoff at 1800", payoff(legs, 1800), 100.0)
check("long put @2000: payoff at 2200", payoff(legs, 2200), -100.0)
check("long put @2000: max loss", max_loss(legs), -100.0)
check("long put @2000: max profit", max_profit(legs), math.inf)
check("long put @2000: breakeven", breakevens(legs), [1900.0])

# ------------------------------------------------------- bull call spread
# buy 2000 C @100 / sell 2100 C @60  ->  net debit 40, width 100
legs = [Leg(CALL, BUY, 2000, 100), Leg(CALL, SELL, 2100, 60)]
check("bull call: payoff at 2050", payoff(legs, 2050), 10.0)
check("bull call: payoff at 2100", payoff(legs, 2100), 60.0)
check("bull call: payoff at 2000", payoff(legs, 2000), -40.0)
check("bull call: max profit", max_profit(legs), 60.0)
check("bull call: max loss", max_loss(legs), -40.0)
check("bull call: breakeven", breakevens(legs), [2040.0])
check("bull call: net premium (debit)", analyse(legs)["net_premium"], 40.0)
check("bull call: net cashflow", analyse(legs)["net_cashflow"], -4000.0)

# -------------------------------------------------------- bear put spread
# buy 2000 P @100 / sell 1900 P @60  ->  net debit 40
legs = [Leg(PUT, BUY, 2000, 100), Leg(PUT, SELL, 1900, 60)]
check("bear put: payoff at 1950", payoff(legs, 1950), 10.0)
check("bear put: payoff at 1900", payoff(legs, 1900), 60.0)
check("bear put: payoff at 2000", payoff(legs, 2000), -40.0)
check("bear put: max profit", max_profit(legs), 60.0)
check("bear put: max loss", max_loss(legs), -40.0)
check("bear put: breakeven", breakevens(legs), [1960.0])

# --------------------------------------------------------------- short call
# sell 2000 C @ 100  ->  keeps premium 100, unlimited risk
legs = [Leg(CALL, SELL, 2000, 100)]
check("short call: payoff at strike", payoff(legs, 2000), 100.0)
check("short call: payoff at 2100", payoff(legs, 2100), 0.0)
check("short call: payoff at 2200", payoff(legs, 2200), -100.0)
check("short call: max profit", max_profit(legs), 100.0)
check("short call: max loss", max_loss(legs), -math.inf)

# --------------------------------------------------------------- short put
legs = [Leg(PUT, SELL, 2000, 100)]
check("short put: payoff at strike", payoff(legs, 2000), 100.0)
check("short put: payoff at 1900", payoff(legs, 1900), 0.0)
check("short put: payoff at 1800", payoff(legs, 1800), -100.0)
check("short put: max profit", max_profit(legs), 100.0)
check("short put: max loss", max_loss(legs), -math.inf)

# ------------------------------------------------------------- long straddle
# buy 2000 C @120 + buy 2000 P @110  ->  debit 230, BE 1770 / 2230
legs = [Leg(CALL, BUY, 2000, 120), Leg(PUT, BUY, 2000, 110)]
check("long straddle: payoff at 2000", payoff(legs, 2000), -230.0)
check("long straddle: payoff at 2100", payoff(legs, 2100), -130.0)
check("long straddle: payoff at 1900", payoff(legs, 1900), -130.0)
check("long straddle: max loss", max_loss(legs), -230.0)
check("long straddle: max profit", max_profit(legs), math.inf)
check("long straddle: breakevens", breakevens(legs), [1770.0, 2230.0])

# ------------------------------------------------------------ short straddle
legs = [Leg(CALL, SELL, 2000, 120), Leg(PUT, SELL, 2000, 110)]
check("short straddle: payoff at 2000", payoff(legs, 2000), 230.0)
check("short straddle: max loss", max_loss(legs), -math.inf)
check("short straddle: max profit", max_profit(legs), 230.0)
check("short straddle: breakevens", breakevens(legs), [1770.0, 2230.0])

# ----------------------------------------------------------------- strangle
# buy 2100 C @80 + buy 1900 P @80  ->  debit 160, BE 1820 / 2180
legs = [Leg(CALL, BUY, 2100, 80), Leg(PUT, BUY, 1900, 80)]
check("strangle: payoff at 2000", payoff(legs, 2000), -160.0)
check("strangle: max loss", max_loss(legs), -160.0)
check("strangle: max profit", max_profit(legs), math.inf)
check("strangle: breakevens (debit 160)", breakevens(legs), [1740.0, 2260.0])

# -------------------------------------------------------------- iron condor
# sell 1900 P @80 / buy 1800 P @40 / sell 2100 C @80 / buy 2200 C @40
# net credit 80, wings 100 wide -> max profit 80, max loss 20, BE 1820/2180
legs = [
    Leg(PUT, SELL, 1900, 80),
    Leg(PUT, BUY, 1800, 40),
    Leg(CALL, SELL, 2100, 80),
    Leg(CALL, BUY, 2200, 40),
]
check("iron condor: net premium (credit)", analyse(legs)["net_premium"], -80.0)
check("iron condor: net cashflow", analyse(legs)["net_cashflow"], 8000.0)
check("iron condor: payoff at 1700", payoff(legs, 1700), -20.0)
check("iron condor: payoff at 1820", payoff(legs, 1820), 0.0)
check("iron condor: payoff at 2000", payoff(legs, 2000), 80.0)
check("iron condor: payoff at 2180", payoff(legs, 2180), 0.0)
check("iron condor: payoff at 2300", payoff(legs, 2300), -20.0)
check("iron condor: max profit", max_profit(legs), 80.0)
check("iron condor: max loss", max_loss(legs), -20.0)
check("iron condor: breakevens", breakevens(legs), [1820.0, 2180.0])

# -------------------------------------------------------------- butterfly
# buy 1900 C @100 / sell 2x 2000 C @100 / buy 2100 C @100
# net debit 0, wings 100 -> max profit 100, max loss 0, BE 1900/2100
legs = [
    Leg(CALL, BUY, 1900, 100),
    Leg(CALL, SELL, 2000, 100),
    Leg(CALL, SELL, 2000, 100),
    Leg(CALL, BUY, 2100, 100),
]
check("butterfly: net premium (debit)", analyse(legs)["net_premium"], 0.0)
check("butterfly: payoff at 1800", payoff(legs, 1800), 0.0)
check("butterfly: payoff at 1950", payoff(legs, 1950), 50.0)
check("butterfly: payoff at 2000", payoff(legs, 2000), 100.0)
check("butterfly: payoff at 2050", payoff(legs, 2050), 50.0)
check("butterfly: payoff at 2200", payoff(legs, 2200), 0.0)
check("butterfly: max profit", max_profit(legs), 100.0)
check("butterfly: max loss", max_loss(legs), 0.0)
check("butterfly: breakevens", breakevens(legs), [1900.0, 2100.0])

# ------------------------------------------------------- put butterfly (mirror)
# buy 2000 P @100 / sell 1900 P @100 / sell 2100 P @100
legs = [
    Leg(PUT, BUY, 1900, 100),
    Leg(PUT, SELL, 2000, 100),
    Leg(PUT, SELL, 2000, 100),
    Leg(PUT, BUY, 2100, 100),
]
check("put butterfly: payoff at 2000", payoff(legs, 2000), 100.0)
check("put butterfly: payoff at 1950", payoff(legs, 1950), 50.0)
check("put butterfly: payoff at 1800", payoff(legs, 1800), 0.0)
check("put butterfly: max profit", max_profit(legs), 100.0)
check("put butterfly: max loss", max_loss(legs), 0.0)
check("put butterfly: breakevens", breakevens(legs), [1900.0, 2100.0])

# ------------------------------------------------------------------- quantity
# qty must scale both intrinsic and premium
legs = [Leg(CALL, BUY, 2000, 100, qty=3)]
check("qty=3: payoff at 2200", payoff(legs, 2200), 300.0)
check("qty=3: payoff at strike", payoff(legs, 2000), -300.0)
check("qty=3: net premium", analyse(legs)["net_premium"], 300.0)
check("qty=3: max loss", max_loss(legs), -300.0)
check("qty=3: lot P&L at 2200", payoff_lots(legs, 2200), 30000.0)

# --------------------------------------------------------- lot size conversion
legs = [Leg(CALL, BUY, 2000, 100)]
bundle = analyse(legs)
check("lots = pnl × 100", bundle["curve"]["lots"][0], round(bundle["curve"]["pnl"][0] * 100, 2))
check("net cashflow", bundle["net_cashflow"], -10000.0)

# ---------------------------------------------------------------- curve shape
legs = [Leg(CALL, BUY, 2000, 100)]
curve = payoff_curve(legs, points=50)
check("curve length", len(curve["prices"]), 50)
check("curve monotonic", all(a <= b for a, b in zip(curve["pnl"], curve["pnl"][1:])), True)
check("curve keys", sorted(curve.keys()), ["lots", "pnl", "prices"])

# ------------------------------------------------- chart range sanity (regression)
# A single-strike structure has a zero strike range. _span is floored at 1.0
# for root-finding, which is too narrow to plot, so payoff_curve uses a
# separate strike-proportional floor. These checks pin that down: without the
# fix every chart of a long call or straddle collapsed to a vertical line.
for name, legs in {
    "single call": [Leg(CALL, BUY, 2000, 100)],
    "single put": [Leg(PUT, BUY, 2000, 100)],
    "straddle": [Leg(CALL, BUY, 2000, 100), Leg(PUT, BUY, 2000, 100)],
    "vertical": [Leg(CALL, BUY, 2000, 100), Leg(CALL, SELL, 2100, 100)],
}.items():
    curve = payoff_curve(legs)
    width = max(curve["prices"]) - min(curve["prices"])
    check(f"chart width positive: {name}", width > 0, True)
    check(f"chart width usable: {name}", width >= 200.0, True)
    check(f"chart strikes inside: {name}",
          min(l.strike for l in legs) >= min(curve["prices"])
          and max(l.strike for l in legs) <= max(curve["prices"]), True)
    check(f"chart samples distinct: {name}", len(set(curve["prices"])) > 1, True)

# Chart range must not depend on how many points are requested.
wide = payoff_curve([Leg(CALL, BUY, 2000, 100)], points=400)
narrow = payoff_curve([Leg(CALL, BUY, 2000, 100)], points=50)
check("chart range stable across resolution",
      round(max(wide["prices"]) - min(wide["prices"]), 2),
      round(max(narrow["prices"]) - min(narrow["prices"]), 2))

# A higher-strike structure scales its axis proportionally, not by a fixed offset.
low = payoff_curve([Leg(CALL, BUY, 200, 5)], points=200)
high = payoff_curve([Leg(CALL, BUY, 20000, 500)], points=200)
check("chart span scales with strike level",
      (max(high["prices"]) - min(high["prices"]))
      > (max(low["prices"]) - min(low["prices"])) * 10, True)

# Explicit bounds must still win over the automatic range.
fixed = payoff_curve([Leg(CALL, BUY, 2000, 100)], lower=1900, upper=2100, points=50)
check("explicit lower honoured", min(fixed["prices"]), 1900.0)
check("explicit upper honoured", max(fixed["prices"]), 2100.0)
print()
if failures:
    print(f"FAILED {len(failures)}/{checks}")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print(f"PASSED all {checks} checks")
