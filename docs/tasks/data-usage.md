# Data team tasks: can we build v2 soil and crop profiles?

Contracts v2 (`data/contracts/v2/`) model the simulation as a Markov chain over
discrete states (`<crop>:skip_stages` for now) whose node carries soil, climate
and financial values. States and edges change those values through **effects**
(`effect.json`). Before switching `registry.json` to v2, we need to know which of
those values we can actually fill for the three profiles (ariquemes-ro, franca-sp,
varginha-mg), and with what support (`observed`, `derived`, `pooled`, `prior`).

Each task ends with a short answer in this file (or a linked note): **available /
proxy / missing**, source, unit, resolution, and support level. Do not turn a
proxy or hypothesis into an observation; keep provenance.

Validate examples with `python -m field_shift.contracts`. The map of every
contract and field, with where each value comes from today, is `docs/contracts-v2.html`
(regenerate with `python -m field_shift.views`).

Owner: data team (huatso) unless a task says otherwise.

## Soil (`soil.json`)

### S1. SiBCS soil order
- Contract field: `soil.order`. The enum now lists the 13 SiBCS orders in English plus
  `Non-Soil` (done by huatso). What is left is the value per profile.
- What we have: R045 (IBGE soil map 1:250,000, WFS `CREN:PD_ORDEM`) is marked as
  ingested; the research notes say the dominant order is Latossolo. But
  `sibcs_order` is `null` in all three `data/profiles/*/soil-profile.json`.
- Questions: where is the ingested layer? Can `build_profiles.py` fill
  `sibcs_order` per profile (dominant order by agricultural-mask area)?
- Deliverable: the dominant order per profile, using the enum names.

### S2. Nitrogen
- Owner: data team.
- Contract field: `soil.N2` (unit is still empty).
- What we have: nothing in the profiles. SoilGrids publishes a `nitrogen` property
  that we did not download.
- Questions: is SoilGrids `nitrogen` (total N) good enough as an initial value? Which
  unit and depth (0-30 cm weighted, like carbon)? Is "total N" what the crop effects
  need, or do we need mineral/available N?
- Deliverable: unit decision for `N2` + value per profile + support level.

### S3. pH
- Contract field: `soil.pH`.
- What we have: `ph_water` per layer from SoilGrids (franca-sp 0-5 cm: 5.2).
- Questions: confirm `soil.pH` = `ph_water` weighted over 0-30 cm. Is there a
  source for the liming effect (pH gain per t/ha of lime) by soil order/texture?

### S4. Soil temperature by depth
- Owner: data team.
- Contract field: `soil.temperature_per_depth`, a list of `{depth (cm), temperature (ºC)}`
  pairs, so depth and temperature always have the same length.
- What we have: nothing.
- Questions: can we get it from ERA5-Land soil temperature levels or NASA POWER
  for the three profiles? What depths and time resolution? Is it static (climatology)
  or does it vary per trajectory day?

## Climate (`climate.json`)

### CL1. Altitude
- Owner: huatso.
- Contract field: `climate.alt` (m).
- What we have: nothing in the profiles.
- Questions: which elevation source (e.g. SRTM, listed among the challenge datasets)?
  Profile centroid or mean over the agricultural mask, like soil?
- Deliverable: altitude per profile + source + support level.

### CL2. Vapor pressure (pre-process)
- Contract field: `climate.weather.relative_humidity` (and the ET0 that uses it).
- What we have: NASA POWER RH2M, daily mean; ET0 uses it in Penman-Monteith.
- Task: add a pre-process step that derives the actual vapor pressure from temperature
  and pressure (POWER also publishes surface pressure), and say whether RH stays as an
  input or becomes derived.
- Deliverable: the formula, the POWER variables it needs, and where it runs in
  `data/pipeline/build_profiles.py`.

## Crops (`crop.json`, used through Markov states)

### C1. Cycle duration per crop (skip_stages)
- Contract field: `duration_days` on each `<crop>:skip_stages` state (number or
  distribution).
- What we have: `data/reference/crop-cycle-assumptions.json` and ZARC windows per
  profile.
- Questions: can each of the 14 v1 crops (soybean, maize_grain, sugarcane, coffee,
  sorghum_grain, wheat, dry_bean, peanut, oat, forage_radish, brachiaria, millet,
  crotalaria, mucuna) get a min/mode/max cycle length? Which ones only have a
  single value?

### C2. Crop effects on soil
- Contract field: `effects` with targets `/soil/N2`, `/soil/pH`, carbon.
- What we have: only `data/reference/soil-crop-response-hypotheses.json` (carbon,
  `uncalibrated_hypothesis`). No N balance per crop.
- Questions: for each crop, is there a citable range for N fixation/uptake and soil
  carbon change per cycle (Embrapa, FAO, literature)? Which crops stay `prior`?
- Deliverable: table crop x target x range x source x support.

### C3. Financial effects
- Contract field: effects on `/financial/cost` (state) and `/financial/revenue`
  (edge, at harvest).
- What we have: CONAB costs, PAM yield/price, `data/reference/economic-benchmarks.json`.
- Questions: can we express cost and revenue per crop and profile as a distribution
  (e.g. triangular from the historical range) instead of a point value?

## Transitions (`markov.json`)

### T1. Coverage of observed transitions
- What we have: v1 `crop-transition-markov.json` per profile (PAM dominant crop,
  1988-2025). Franca-sp only observes maize_grain, sugarcane and coffee; the
  other 11 crops have zero counts.
- Questions: for each profile, which rows are `observed`, which need `pooled` (e.g.
  same state or region) and which stay `prior`? Is the v1 Dirichlet prior
  (alpha 0.5) kept as a separate `prior` layer or folded into the probability?
- Deliverable: per-profile table of rows by support level. See
  `data/contracts/v2/examples/markov.franca-sp-observed.json` for the target shape.

## Summary to fill

| Field | ariquemes-ro | franca-sp | varginha-mg | Source | Support |
|---|---|---|---|---|---|
| soil.order | | | | | |
| soil.N2 | | | | | |
| soil.pH | | | | | |
| soil.temperature_per_depth | | | | | |
| soil.organic_carbon | v1 | v1 | v1 | SoilGrids soc | derived |
| soil.available_water_capacity | v1 | v1 | v1 | SoilGrids + Saxton & Rawls | derived |
| climate.alt | | | | | |
| climate.weather.et0 | v1 | v1 | v1 | NASA POWER, FAO-56 | derived |
| crop.kc_annual_effective | v1 | v1 | v1 | FAO-56 | prior |
| crop.planting_windows | v1 | v1 | v1 | MAPA ZARC | observed |
| financial yield / price | v1 | v1 | v1 | PAM | observed |
| crop duration_days (14 crops) | | | | | |
| crop soil effects | | | | | |
| crop cost / revenue | | | | | |
| observed transitions | | | | | |

Go/no-go for v2: every row has at least a `prior` with provenance, and the gaps
are written down.
