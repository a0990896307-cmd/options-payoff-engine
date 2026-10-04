"""
Options payoff engine.

Leg-based design: a strategy is a list of legs, and every output
(max profit, max loss, breakeven, payoff curve) derives from one
payoff function. Nothing is special-cased per strategy type, so
exotic spreads fall out for free.

Leg P&L is:
    P&L(S) = Σ  qty × sign × (intrinsic(S, K, type) − premium)

where sign is +1 for BUY and −1 for SELL. That single expression is
correct for every leg, and the sum is correct for every strategy.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

LOT_SIZE = 100  # NIFTY lot multiplier


class OptionType(str, Enum):
    CALL = "CALL"
    PUT = "PUT"


class Direction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass(frozen=True)
class Leg:
    type: OptionType
    direction: Direction
    strike: float
    premium: float
    qty: int = 1

    def intrinsic(self, spot: float) -> float:
        """Value of one unit at expiry, before premium."""
        if self.type is OptionType.CALL:
            return max(0.0, spot - self.strike)
        return max(0.0, self.strike - spot)

    @property
    def sign(self) -> int:
        return 1 if self.direction is Direction.BUY else -1

    @property
    def cashflow(self) -> float:
        """Premium cashflow per unit: negative = paid, positive = received."""
        return -self.sign * self.premium


def payoff(legs: list[Leg], spot: float) -> float:
    """Net P&L per unit of underlying at expiry."""
    return sum(leg.qty * leg.sign * (leg.intrinsic(spot) - leg.premium) for leg in legs)


def payoff_lots(legs: list[Leg], spot: float) -> float:
    """Net P&L in currency at NIFTY lot size."""
    return payoff(legs, spot) * LOT_SIZE


# --------------------------------------------------------------- slope analysis

def _slope_high(legs: list[Leg]) -> int:
    """Slope once spot exceeds every strike (puts contribute nothing)."""
    return sum(leg.sign * leg.qty for leg in legs if leg.type is OptionType.CALL)


def _slope_low(legs: list[Leg]) -> int:
    """Slope once spot falls below every strike (slope flips for puts)."""
    return -sum(leg.sign * leg.qty for leg in legs if leg.type is OptionType.PUT)


def _strikes(legs: list[Leg]) -> list[float]:
    return sorted({leg.strike for leg in legs})


def _span(legs: list[Leg]) -> float:
    strikes = _strikes(legs)
    return max(strikes[-1] - strikes[0], 1.0)


def _sample_points(legs: list[Leg]) -> list[float]:
    """
    Points to evaluate for extrema and roots.

    Every strike, plus one point inside each unbounded tail. On a tail
    the function is linear, so any point in it is a valid representative
    when the tail is not the side holding the extreme.
    """
    strikes = _strikes(legs)
    pad = _span(legs)
    return [strikes[0] - pad, *strikes, strikes[-1] + pad]


# ------------------------------------------------------------------- extremes

def max_profit(legs: list[Leg]) -> float:
    """Best possible P&L per unit. +inf when unbounded above."""
    if _slope_high(legs) > 0 or _slope_low(legs) < 0:
        return math.inf
    return max(payoff(legs, s) for s in _sample_points(legs))


def max_loss(legs: list[Leg]) -> float:
    """Worst possible P&L per unit. -inf when unbounded below."""
    if _slope_high(legs) < 0 or _slope_low(legs) > 0:
        return -math.inf
    return min(payoff(legs, s) for s in _sample_points(legs))


# ----------------------------------------------------------------- breakevens

def breakevens(legs: list[Leg]) -> list[float]:
    """
    Exact breakeven prices per unit.

    Payoff is piecewise linear with slope changes only at strikes, so
    roots are solved analytically segment by segment rather than by
    sampling. Search range covers strikes extended by the total premium,
    because an unbounded leg's breakeven sits outside the strike range
    (e.g. a long call breakevens above its own strike).
    """
    strikes = _strikes(legs)
    reach = sum(leg.qty * leg.premium for leg in legs) + _span(legs) + 10.0
    points = [strikes[0] - reach, *strikes, strikes[-1] + reach]

    strikes_set = set(strikes)
    roots: list[float] = []
    for a, b in zip(points, points[1:]):
        fa, fb = payoff(legs, a), payoff(legs, b)
        if abs(fb - fa) < 1e-12:
            # Flat segment. Identically zero is a real breakeven only at a
            # strike (a genuine vertex); the artificial range endpoints are
            # not roots and must not be reported.
            if abs(fa) < 1e-9 and a in strikes_set:
                roots.append(a)
            continue
        x = a - fa * (b - a) / (fb - fa)
        if points[0] < x < points[-1]:
            roots.append(round(x, 4))
    return sorted(set(roots))


# ----------------------------------------------------------------------- curve

def _chart_span(legs: list[Leg]) -> float:
    """
    Half-width of the plotted price range.

    Distinct from _span, which is sized for root-finding: a 1.0 floor is
    enough to place a sample point inside an unbounded tail, but it is
    far too narrow to plot. A single-strike structure such as a long
    call or a straddle has a zero strike range, so without this the
    chart collapses to a vertical line at the strike.

    The floor is therefore proportional to the strike level, which keeps
    the axis sensible for a NIFTY strike near 20000 and for a SPX strike
    near 600 without hardcoding either.
    """
    strikes = _strikes(legs)
    spread = strikes[-1] - strikes[0]
    floor = max(abs(strikes[0]) * 0.10, 1.0)
    return max(spread * 0.6, floor)


def payoff_curve(
    legs: list[Leg],
    lower: float | None = None,
    upper: float | None = None,
    points: int = 200,
) -> dict[str, list[float]]:
    """Sampled payoff curve for charting."""
    strikes = _strikes(legs)
    pad = _chart_span(legs)
    lo = lower if lower is not None else strikes[0] - pad
    hi = upper if upper is not None else strikes[-1] + pad
    if hi <= lo:
        lo, hi = strikes[0] - 50, strikes[0] + 50

    step = (hi - lo) / max(points - 1, 1)
    prices = [round(lo + step * i, 2) for i in range(points)]
    pnl = [round(payoff(legs, p), 4) for p in prices]
    return {
        "prices": prices,
        "pnl": pnl,
        "lots": [round(v * LOT_SIZE, 2) for v in pnl],
    }


# --------------------------------------------------------------------- bundle

def analyse(legs: list[Leg]) -> dict:
    """Full analytics for one strategy."""
    # Signed premium: bought legs add, sold legs subtract.
    # Positive = net debit, negative = net credit.
    net = sum(leg.qty * leg.sign * leg.premium for leg in legs)
    return {
        "max_profit": max_profit(legs),
        "max_loss": max_loss(legs),
        "breakevens": breakevens(legs),
        "net_premium": round(net, 4),          # >0 debit, <0 credit
        "net_cashflow": round(-net * LOT_SIZE, 2),  # >0 received, <0 paid
        "lot_size": LOT_SIZE,
        "curve": payoff_curve(legs),
    }


def format_unbounded(value: float) -> str:
    if value == math.inf:
        return "Unlimited"
    if value == -math.inf:
        return "Unlimited loss"
    return f"{value:.2f}"