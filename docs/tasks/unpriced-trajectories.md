# Epic: price every trajectory

Owner: @Gabriel-ASM (economic inputs). Written on 2026-11-15 as a brief for a person or an AI assistant picking this up.

## The problem in one paragraph

The Monte Carlo engine computes the present value (BRL/ha, 5 years) of each simulated trajectory. A trajectory
that harvests a crop without complete economic inputs cannot be priced, so it is **left out of the value
statistics**. Today that removes between a quarter and two thirds of the trajectories of the "what the region
usually does" scenario. The surviving ones are not a random sample: they are the trajectories that avoided
those crops, so the reported median and range are biased. The front shows the share left out, but the number
next to it is still misleading.

## Measured today (seed 2026, 20,000 trajectories, chain scenario)

| Profile | Starting crop | Trajectories priced | Crops that cannot be priced | Missing input |
|---|---|---|---|---|
| ariquemes-ro | soybean | 72.8% | peanut | municipal yield |
| ariquemes-ro | maize_grain | 73.9% | peanut | municipal yield |
| franca-sp | soybean | 51.0% | sorghum_grain, dry_bean, millet | municipal yield |
| franca-sp | maize_grain | 55.1% | sorghum_grain, dry_bean, millet | municipal yield |
| varginha-mg | soybean | 34.8% | sorghum_grain, wheat, peanut, millet | municipal yield |
| varginha-mg | maize_grain | 47.5% | sorghum_grain, wheat, peanut, millet | municipal yield |

Starting from sugarcane every trajectory is priced, because the field stays in sugarcane for the horizon.

In every case the entry exists in `economics.crop_inputs` with price and cost, and the only missing field is
`yield_kg_ha_median_2021_2025` (IBGE PAM municipal median). The municipality did not report that crop in
2021-2025, so `data/pipeline/build_economic_benchmarks.py` sets `eligible_for_economic_comparison: false`
and lists the crop in `economic_exclusions`.

## Where things are

| What | Where |
|---|---|
| Economic inputs are built | `data/pipeline/build_economic_benchmarks.py` (`eligible_for_economic_comparison`, `economic_exclusions`) |
| Inputs reach the engine | `field_shift/engines/payload.py` -> `profile_payload()["economics"]` |
| The pricing rule | `field_shift/engines/tables.py::_economics` (`harvest_priced`, `formation_priced`) |
| Where a trajectory loses its price | `field_shift/engines/monte_carlo.py::harvest`, `plant`, `charge_formation` (`state.priced`) |
| What the client receives | `field_shift/engines/summary.py` (`priced_share`, `value`) |
| The same rule in the offline page | `field_shift/front/analysis.js::scoreTrajectoryVpl` |

Reproduce the table:

```bash
uv run python - <<'PY'
import numpy as np
from field_shift.engines.run import tables_for
from field_shift.engines.monte_carlo import Policy, simulate
tables = tables_for("franca-sp")
result = simulate(np, tables, Policy(tables.crops.index("soybean")), 2026, 20000)
print(result["priced"].mean(), [c for c, ok in zip(tables.crops, tables.harvest_priced) if not ok])
PY
```

## What "done" means

1. Every crop that the chain of a profile can reach has yield, price and cost, **each with `support` and
   `provenance`** (observed / derived / pooled / prior, as in `data/contracts/v2/effect.json`).
2. `priced_share` is 1.0 for the three profiles from every selectable starting crop, or the remaining gap is
   explained per crop in this file.
3. `uv run pytest` and `node --test tests/test_front.cjs` pass, and `python -m field_shift.front` still
   regenerates `docs/visualizacao.html`.

## Options, in the order we would try them

1. **Pool the yield from a wider area.** When the municipality has no PAM yield for a crop, use the
   microregion, then the state (UF) median for 2021-2025. Mark it `support: "pooled"` and say which level was
   used. This is the same idea the cost panel already uses (`match_level`: "mesma UF · outro município").
2. **Restrict the chain instead.** If a crop has no yield anywhere near the municipality, it is probably not
   grown there; its edge mass comes from the top-5 area shares of other years. Consider dropping the crop from
   that profile's chain (`field_shift/ingest/chains.py`, as was done for coffee) rather than inventing a yield.
3. **Never** fill a missing yield with a national average silently, a constant, or zero. A value without
   provenance is worse than an excluded trajectory.

Options 1 and 2 can be combined per crop. Whatever is chosen, the engine needs no change: it prices a crop as
soon as its three inputs are finite and the crop is flagged eligible.

## Out of scope here

- Random events (pests, climate extremes): the engine refuses them because no profile has event probabilities.
  That is a separate data task.
- Editable crop profiles on the web, and reading news with an LLM to configure them through the contract API:
  still under discussion.
