# Engine validation: what was checked and what the results say

Checked on 2026-11-15 at commit `7513478` (local `main`). Everything here can be re-run with the commands given.
Field Shift results are exploratory; this page says how far they can be trusted, and where they cannot.

## 1. The Python engine reproduces the team's JavaScript simulator

The backend engine (`field_shift/engines`) is a port of the simulator in `field_shift/front/analysis.js`.
Both draw their own random numbers, so they are compared statistically.

    uv run python tests/parity/compare.py 20000 2026

| | |
|---|---|
| JS compared | `analysis.js` after the team's commit `7a836bf` (total nitrogen in the transitions and the soil score) |
| Cases | 3 municipalities × 3 starting crops (soybean, maize, sugarcane) |
| Trajectories | 20,000 per side per case |
| Statistics compared | 144: share ending in each crop, share of the most frequent sequences, priced share, mean present value |
| Largest difference | \|z\| = 2.9 |
| Above \|z\| = 3 | none (8 above 2; about 7 are expected by chance among 144) |

History: before the engine was aligned with `8788667`, 44 of the 144 statistics differed by more than 3 standard
errors (largest 35); after it, none (largest 2.7, seed 7). `7a836bf` reopened the gap (15 statistics above 4, largest
10: Franca from soybean ended in sugarcane in 69.1% of trajectories in the JS, 71.9% in Python) until its total-N
model was ported (`97bc5fd`); Franca from soybean is now 69.05% JS, 69.03% Python. The comparison is the regression
check for every future change of either side.

## 2. Automated tests

    uv run pytest                      # 76 pass, 10 skipped (need a real MongoDB)
    cd ctrlaltespaco && npm test       # 11 pass

The 10 skipped tests exercise ingestion and the API against a real MongoDB and were not run for this page.

## 3. What the results look like

Regional chain from each starting crop, 100,000 trajectories, seeds 1, 2 and 3, on GPU (about 6 s per run).
"Best" below is the sequence with the highest median present value among those with at least 20 priced
trajectories (the recommendation threshold in `visualization-run-settings.json`). The product ranks with a 0–10
score that also weighs downside, soil, water and sample support, so its pick can differ; this proxy is enough to
judge the evidence behind a pick.

| Municipality, start | Most frequent sequence (share, median R$/ha) | Best sequence (trajectories behind it, median R$/ha) |
|---|---|---|
| Ariquemes, soybean | soybean → sugarcane (4.8%, 2,940) | soybean ×4 → peanut → maize ×3 (28–34, 6,900–7,200) |
| Ariquemes, maize | maize → sugarcane (3.5%, 4,950) | maize ×3 → peanut → soybean ×3 (32–45, 10,300–10,800) |
| Ariquemes, sugarcane | sugarcane (100%, 12,533) | the same, no alternative |
| Franca, soybean | soybean → sugarcane (24%, −1,930) | soybean → dry bean ×2 → sugarcane (32–44, 20,800–21,800) |
| Franca, maize | maize → sugarcane (19%, −5,268) | maize → dry bean ×2 → sugarcane (20–35, 17,900–18,800) |
| Franca, sugarcane | sugarcane (100%, 5,130) | the same, no alternative |
| Varginha, soybean | soybean → sugarcane (9%, −23,100) | maize and dry bean alternating (21–24, 12,900–13,800) |
| Varginha, maize | maize → sugarcane (3.8%, −21,300) | maize and dry bean alternating (23–26, 15,600–16,100) |
| Varginha, sugarcane | sugarcane (100%, −15,910) | the same, no alternative |

Every trajectory is priced (unpriced share 0 in all 27 runs).

    uv run python tests/parity/evaluate_results.py 100000 out.json

## 4. What to trust, and what not yet

**Holds.** The engine matches the reference simulator; the same sequence wins
under three seeds in Ariquemes and Franca; no trajectory is left without a price.

**Findings that limit the result.**

1. **The recommendation rests on very few trajectories.** The best sequence is followed by 20 to 45 of 100,000
   trajectories (0.02–0.05%), so its median moves by about 5% between seeds, and in Varginha the winning sequence
   itself changes with the seed. Sequences that reach the 20-sample threshold cover only 21–48% of the
   trajectories. The regional chain rarely visits the sequences worth recommending; simulating the candidate
   sequences directly as fixed rotations, each with the full sample, would give them real evidence.
2. **Repeated soybean can be recommended.** In Ariquemes the best sequence from soybean opens with four soybean crops
   in a row, and from maize it ends with three. Soybean follows soybean in up to 13% of trajectories (Ariquemes
   from soybean; 7% in Franca from soybean). The repeated-crop
   penalty is not enough to keep it out; the nitrogen balance that should do this is implemented but switched off
   for lack of sourced fixation and residual-credit values.
3. **Dry bean drives every recommendation.** Adding two dry bean crops to soybean → sugarcane in Franca moves the
   median from −1,930 to about +21,000 R$/ha. The dry bean price, yield and cost in the profiles should be
   reviewed by the data team before this is shown as advice.
4. **Sugarcane inside a five-year horizon looks worse than it is.** The formation cost is paid in full and only the
   cuts that fit in five years are counted, with no value for the standing field at the end. That is why what the
   region usually does (… → sugarcane) has a negative median in Franca and Varginha.
5. **Starting from sugarcane there is no decision.** All 100,000 trajectories follow one sequence and end in
   fallow after the cuts, so the result is a valuation of the standing field, not a comparison.
6. **Sugarcane percentiles do not move with the seed.** P5, median and P95 are identical, to the R$, across three
   seeds (only the tail mean changes), which means the cane value takes few distinct levels. Likely a consequence
   of yield by water class; not confirmed.

**Out of scope of the model:** pests, wind, and anything outside the three municipalities.
