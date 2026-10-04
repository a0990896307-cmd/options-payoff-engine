# Options Payoff Engine

Multi-leg options payoff and risk engine in Python. Analytic breakevens,
correct handling of long/short sides, and friction modelled as
configuration rather than hardcoded assumptions.

Written for a trading platform MVP; this repository contains the core
engine and its test suite.

## Why analytic breakevens

The common approach is to solve `payoff(S) = 0` numerically, for example by
scanning a spot grid and interpolating between samples. That makes the
answer a function of the grid resolution, and it silently returns
inaccurate values near expiry where the payoff transitions sharply.

For payoff structures that are piecewise linear in the underlying
`S`, each breakeven is simply the root of a linear segment and can be
solved in closed form. The engine therefore identifies the segments from
the net signed position of every leg and solves each directly. Results are
exact and independent of any sampling parameter, and the engine reports
the number of breakevens it found so degenerate cases stay visible instead
of being smoothed over.

## Model

Each leg is defined by:

| Field | Meaning |
|---|---|
| `kind` | `CALL` or `PUT` |
| `side` | `BUY` or `SELL` |
| `strike` | Strike price `K` |
| `premium` | Premium paid or received per unit, net of fees |
| `qty` | Number of contracts, always positive |

Payoff at expiry for underlying price `S`:

```
payoff(S) = Σ qty_i · dir_i · multiplier · value_i(S) - net_premium(S)
```

where `dir_i` is `+1` for `BUY` and `-1` for `SELL`, `multiplier` is the
contract size, and `value_i(S)` is the intrinsic value of the leg:

```
CALL: max(S - K, 0)
PUT:  max(K - S, 0)
```

A long position receives `+1` on that intrinsic value, a short position
pays it out. `net_premium` is the signed total of all premiums, so a net
credit structure reports a positive net premium in the profit line.

A `Leg` with `qty = 0` contributes nothing, which is how a vertical or
calendar is expressed: two legs sharing a strike, one opened long and one
short.

## Engine surface

- `payoff_at(S)` — net P&L at expiry for a given underlying price
- `max_profit()` / `max_loss()` — exact from the piecewise-linear payoff
- `breakevens()` — analytic segment roots, no scanning
- `curve(points)` — sampled payoff curve for charting
- `analyse()` — all of the above plus slope and aggregate greeks

Multipliers and lot size are parameters rather than constants. Indian
NIFTY options use a lot size of 100, US equity options a multiplier of
100, and index or crypto derivatives differ again, so the engine takes
both as arguments and defaults to the standard equity case.

## Tests

85 automated checks, no third-party dependencies:

```bash
python backend/tests/test_payoff.py
```

The suite is a standalone runner rather than pytest so it needs nothing
installed beyond the standard library. Each check prints `ok` or the
expected and actual values, and the process exits non-zero on any failure,
so it drops straight into CI as-is.

Coverage includes:

- single long call and put, both directions
- vertical spreads and straddles, both directions
- iron condors and butterflies
- exact breakevens verified against hand-computed values
- agreement between analytic and numeric breakevens on random structures
- zero-premium and zero-quantity degenerate legs
- boundary strikes where `S` equals `K`
- non-default multipliers and lot sizes
- symmetry: reversing every side mirrors the payoff line
- max profit and max loss consistent with the sampled curve

Degenerate inputs are tested deliberately rather than excluded. A payoff
engine that raises on an unusual structure is worse than one that returns a
defined answer and lets the caller decide, so unsupported cases return
`None` and are asserted as such.

## Layout

```
backend/app/payoff.py        engine
backend/tests/test_payoff.py test suite
```

## Status

Engine and tests are complete. The REST layer and web front end for the
platform MVP are separate deliverables and not included here.

## Licence

MIT.