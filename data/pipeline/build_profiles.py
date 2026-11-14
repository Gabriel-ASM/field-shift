"""Transform the downloaded NASA POWER and SoilGrids responses into demo profiles.

Raw API responses remain unchanged under data/raw/. This script normalizes the
daily climate rows, derives a reference soil-water bucket and Markov counts, and
writes provenance-tracked municipal profiles. It does not create field
observations, crop yields, or crop recommendations.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import mean

from contract_registry import current_contract_version, validate_contract


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
RAW_POWER = DATA / "raw" / "nasa_power"
RAW_SOIL = DATA / "raw" / "soilgrids"
RAW_IBGE = DATA / "raw" / "ibge"
PROFILES = DATA / "profiles"
FIRST_DAY = date(1981, 1, 1)
LAST_DAY = date(2026, 11, 6)
TRAINING_LAST_DAY = date(2025, 12, 31)
SPINUP_LAST_YEAR = 1982
PSEUDOCOUNT = 0.5
MIN_DIRECT_TRANSITIONS = 30
ACTION = "reference_et0_demand"
DEPTHS = [(0, 5), (5, 15), (15, 30), (30, 60), (60, 100)]
STATE_IDS = {"baixa": "water_low", "media": "water_medium", "alta": "water_high"}
STATE_ORDER = ("baixa", "media", "alta")
LOCATIONS = [
    {"id": "ariquemes-ro", "municipality": "Ariquemes", "uf": "RO", "ibge_code": "1100023", "label": "Rondônia", "source_stem": "ariquemes", "lon": -62.957184, "lat": -9.951874},
    {"id": "franca-sp", "municipality": "Franca", "uf": "SP", "ibge_code": "3516200", "label": "São Paulo", "source_stem": "franca", "lon": -47.381550, "lat": -20.555247},
    {"id": "varginha-mg", "municipality": "Varginha", "uf": "MG", "ibge_code": "3170701", "label": "Minas Gerais", "source_stem": "varginha", "lon": -45.408932, "lat": -21.557495},
]
POWER_FIELDS = (
    ("PRECTOTCORR", "precipitation_mm"),
    ("T2M_MAX", "tmax_c"),
    ("T2M_MIN", "tmin_c"),
    ("ALLSKY_SFC_SW_DWN", "solar_mj_m2_day"),
    ("RH2M", "relative_humidity_pct"),
    ("WS2M", "wind_2m_ms"),
)


def read_json(path: Path):
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def ring_area_centroid(ring: list[list[float]]) -> tuple[float, float, float]:
    area2 = cx = cy = 0.0
    for first, second in zip(ring, ring[1:]):
        cross = first[0] * second[1] - second[0] * first[1]
        area2 += cross
        cx += (first[0] + second[0]) * cross
        cy += (first[1] + second[1]) * cross
    if abs(area2) < 1e-15:
        raise ValueError("IBGE polygon has a degenerate ring")
    return area2 / 2, cx / (3 * area2), cy / (3 * area2)


def ibge_area_centroid(code: str) -> tuple[float, float]:
    """Area-weighted municipality centroid from the downloaded IBGE GeoJSON."""
    geojson = read_json(RAW_IBGE / f"ibge-malha-municipal-{code}.geojson")
    geometry = geojson["features"][0]["geometry"]
    polygons = [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]
    weighted_area = weighted_lon = weighted_lat = 0.0
    for polygon in polygons:
        for index, ring in enumerate(polygon):
            signed_area, lon, lat = ring_area_centroid(ring)
            area = abs(signed_area) * (1 if index == 0 else -1)
            weighted_area += area
            weighted_lon += area * lon
            weighted_lat += area * lat
    if weighted_area <= 0:
        raise ValueError(f"Invalid IBGE polygon area for {code}")
    return weighted_lon / weighted_area, weighted_lat / weighted_area


def extraterrestrial_radiation(latitude_degrees: float, day_of_year: int) -> float:
    """FAO-56 daily Ra in MJ m-2 day-1."""
    latitude = math.radians(latitude_degrees)
    dr = 1 + 0.033 * math.cos(2 * math.pi * day_of_year / 365)
    declination = 0.409 * math.sin(2 * math.pi * day_of_year / 365 - 1.39)
    sunset_angle = math.acos(max(-1.0, min(1.0, -math.tan(latitude) * math.tan(declination))))
    return (24 * 60 / math.pi) * 0.0820 * dr * (
        sunset_angle * math.sin(latitude) * math.sin(declination)
        + math.cos(latitude) * math.cos(declination) * math.sin(sunset_angle)
    )


def saturation_vapour_pressure(temp_c: float) -> float:
    return 0.6108 * math.exp(17.27 * temp_c / (temp_c + 237.3))


def eto_fao56(row: dict, latitude: float, elevation_m: float) -> tuple[float | None, str | None]:
    tmax, tmin = row.get("tmax_c"), row.get("tmin_c")
    if tmax is None or tmin is None:
        return None, None
    tmean = (tmax + tmin) / 2
    ra = extraterrestrial_radiation(latitude, row["_date"].timetuple().tm_yday)
    rs = row.get("solar_mj_m2_day")
    if rs is None:
        return max(0.0, 0.0023 * (tmean + 17.8) * math.sqrt(max(0.0, tmax - tmin)) * ra), "Hargreaves-Samani; radiação solar ausente"

    rh = row.get("relative_humidity_pct")
    wind = row.get("wind_2m_ms")
    if rh is None or wind is None:
        return None, None
    es_max = saturation_vapour_pressure(tmax)
    es_min = saturation_vapour_pressure(tmin)
    es = (es_max + es_min) / 2
    # POWER daily RH2M is a daily mean; this approximation is explicitly recorded.
    ea = max(0.0, min(es, es * rh / 100))
    delta = 4098 * saturation_vapour_pressure(tmean) / (tmean + 237.3) ** 2
    pressure = 101.3 * ((293 - 0.0065 * elevation_m) / 293) ** 5.26
    gamma = 0.000665 * pressure
    rso = max(0.01, (0.75 + 2e-5 * elevation_m) * ra)
    rns = 0.77 * rs
    cloud_ratio = max(0.0, min(1.0, rs / rso))
    sigma = 4.903e-9
    rnl = sigma * (((tmax + 273.16) ** 4 + (tmin + 273.16) ** 4) / 2) * (
        0.34 - 0.14 * math.sqrt(max(0.0, ea))
    ) * (1.35 * cloud_ratio - 0.35)
    rn = rns - rnl
    eto = (0.408 * delta * rn + gamma * (900 / (tmean + 273)) * wind * (es - ea)) / (
        delta + gamma * (1 + 0.34 * wind)
    )
    return max(0.0, eto), "FAO-56 Penman-Monteith; RH2M média diária"


def power_rows(location: dict) -> list[dict]:
    raw = read_json(RAW_POWER / f"nasa-power-daily-{location['source_stem']}-1981-20261106.json")
    params = raw["properties"]["parameter"]
    point = raw["geometry"]["coordinates"]
    rows = []
    for key in sorted(params["PRECTOTCORR"]):
        day = datetime.strptime(key, "%Y%m%d").date()
        row = {"_date": day, "location_id": location["id"], "time_basis": "local_solar_time", "timezone": None}
        missing = []
        for source_name, field in POWER_FIELDS:
            value = params[source_name][key]
            if value is None or value == raw["header"]["fill_value"]:
                row[field] = None
                missing.append(field)
            else:
                row[field] = float(value)
        row["source"] = "NASA POWER Daily API v2.10.3; MERRA2/SRB/SYN1DEG/POWER"
        row["source_status"] = None
        eto, method = eto_fao56(row, location["lat"], float(point[2]))
        row["eto_mm_day"] = eto
        row["eto_method"] = method
        row["quality_valid"] = row["precipitation_mm"] is not None and row["tmax_c"] is not None and row["tmin_c"] is not None and eto is not None
        flags = []
        if "solar_mj_m2_day" in missing:
            flags.append("solar_missing_hargreaves_eto_fallback")
        if not row["quality_valid"]:
            flags.append("required_climate_value_missing")
        row["quality_flags"] = flags
        row["missing_variables"] = missing
        rows.append(row)
    return rows


def soil_profile(location: dict) -> dict:
    raw = read_json(RAW_SOIL / f"soilgrids-v2-{location['source_stem']}-mean.json")
    layers = {layer["name"]: layer for layer in raw["properties"]["layers"]}
    output_layers = []
    total_awc = 0.0
    weighted = defaultdict(float)
    for top, bottom in DEPTHS:
        label = f"{top}-{bottom}cm"
        values = {}
        for key, field in (("clay", "clay_pct"), ("sand", "sand_pct"), ("silt", "silt_pct"), ("phh2o", "ph_water"), ("soc", "organic_carbon_g_kg")):
            layer = layers[key]
            entry = next(depth for depth in layer["depths"] if depth["label"] == label)
            value = entry["values"]["mean"]
            if value is None:
                raise ValueError(f"SoilGrids returned no mean for {location['id']} {key} {label}")
            values[field] = float(value) / float(layer["unit_measure"]["d_factor"])
        sand = values["sand_pct"] / 100
        clay = values["clay_pct"] / 100
        # Saxton & Rawls (2006) uses percent OM and texture fractions 0-1.
        organic_matter_pct = values["organic_carbon_g_kg"] / 10 * 1.724
        theta_1500_t = (-0.024 * sand + 0.487 * clay + 0.006 * organic_matter_pct
            + 0.005 * sand * organic_matter_pct - 0.013 * clay * organic_matter_pct
            + 0.068 * sand * clay + 0.031)
        theta_1500 = theta_1500_t + (0.14 * theta_1500_t - 0.02)
        theta_33_t = (-0.251 * sand + 0.195 * clay + 0.011 * organic_matter_pct
            + 0.006 * sand * organic_matter_pct - 0.027 * clay * organic_matter_pct
            + 0.452 * sand * clay + 0.299)
        theta_33 = theta_33_t + (1.283 * theta_33_t ** 2 - 0.374 * theta_33_t - 0.015)
        available_fraction = max(0.0, theta_33 - theta_1500)
        thickness_mm = (bottom - top) * 10
        awc_mm = available_fraction * thickness_mm
        total_awc += awc_mm
        for field, value in values.items():
            weighted[field] += value * (bottom - top)
        output_layers.append({
            "depth_top_cm": top, "depth_bottom_cm": bottom, **values,
            "organic_matter_pct_for_pedotransfer": organic_matter_pct,
            "theta_33_volumetric": theta_33,
            "theta_1500_volumetric": theta_1500,
            "available_water_fraction_volumetric": available_fraction,
            "available_water_capacity_mm": awc_mm,
        })
    avg = {key: value / 100 for key, value in weighted.items()}
    return {
        "location_id": location["id"], "scope": "grid_cell", "reference_date": None,
        "source": "ISRIC SoilGrids v2.0 properties API (mean prediction); AWC derived by Saxton & Rawls (2006)",
        "sample_point": {"longitude": location["lon"], "latitude": location["lat"], "basis": "centroide de área da malha municipal IBGE consultada; não é posição de talhão"},
        "depth_cm": 100, "available_water_capacity_mm": total_awc,
        "available_water_fraction": None, "texture_class": None, **avg,
        "sibcs_order": None, "layers": output_layers,
        "quality": {
            "status": "mapped_estimate",
            "flags": ["soilgrids_mean_prediction", "awc_pedotransfer_derived", "municipality_centroid_not_field_sample", "not_a_field_soil_analysis"],
            "uncertainty": "Média espacial SoilGrids em célula de 250 m. Sem amostra de campo e sem quantis inferior/superior no download; a célula no centroide pode não representar área agrícola do município.",
        },
    }


def quantile(values: list[float], q: float) -> float:
    values = sorted(values)
    if len(values) == 1:
        return values[0]
    pos = (len(values) - 1) * q
    lower = math.floor(pos)
    fraction = pos - lower
    return values[lower] * (1 - fraction) + values[min(lower + 1, len(values) - 1)] * fraction


def water_class(fraction: float) -> str:
    if fraction <= 1 / 3:
        return "baixa"
    if fraction <= 2 / 3:
        return "media"
    return "alta"


def climate_history(rows: list[dict], awc_mm: float) -> tuple[dict, list[dict], dict]:
    training = [row for row in rows if row["_date"] <= TRAINING_LAST_DAY and row["quality_valid"]]
    if not training or training[0]["_date"] != FIRST_DAY or training[-1]["_date"] != TRAINING_LAST_DAY:
        raise ValueError("Training climate must cover complete years 1981-2025")

    periods = []
    storage = awc_mm * 0.5  # explicit spin-up condition, not a field measurement
    active_key = None
    group = []
    period_start_storage = storage
    for row in training:
        day = row["_date"]
        key = (day.year, day.month, 0 if day.day <= 15 else 1)
        if active_key is not None and key != active_key:
            periods.append((active_key, group, period_start_storage, storage))
            group = []
            period_start_storage = storage
        active_key = key
        group.append(row)
        precipitation = row["precipitation_mm"]
        eto = row["eto_mm_day"]
        storage = min(awc_mm, storage + precipitation)
        storage -= min(storage, eto)  # reference ET0 demand; Kc=1 by definition

    if active_key is not None:
        periods.append((active_key, group, period_start_storage, storage))
    if len(periods) != 45 * 24:
        raise ValueError(f"Expected 1080 complete half-month periods, got {len(periods)}")

    monthly_period_rain = defaultdict(list)
    for (year, month, half), group, _, _ in periods:
        monthly_period_rain[(month, half)].append(sum(row["precipitation_mm"] for row in group))
    thresholds = {
        key: (quantile(values, 0.20), quantile(values, 0.80))
        for key, values in monthly_period_rain.items()
    }
    history: dict[str, list[str]] = defaultdict(list)
    direct_counts: dict[tuple[str, str], Counter] = defaultdict(Counter)
    observed_context: Counter = Counter()
    period_values = []
    for (year, month, half), group, before, after in periods:
        rain = sum(row["precipitation_mm"] for row in group)
        low, high = thresholds[(month, half)]
        environment = "dry" if rain == 0 or rain < low else "wet" if rain > high else "normal"
        start_state = water_class(before / awc_mm)
        end_state = water_class(after / awc_mm)
        period_values.append({
            "year": year, "month": month, "half": half + 1,
            "environment": environment, "rainfall_mm": rain,
            "water_fraction_start": before / awc_mm,
            "water_fraction_end": after / awc_mm,
            "state_start": start_state, "state_end": end_state,
        })
        history[str(year)].append(environment)
        if year > SPINUP_LAST_YEAR:
            direct_counts[(start_state, environment)][end_state] += 1
            observed_context[(start_state, environment)] += 1

    transitions = []
    for state in STATE_ORDER:
        pooled = Counter()
        for env in ("dry", "normal", "wet"):
            pooled.update(direct_counts[(state, env)])
        if not pooled:
            raise ValueError(f"No derived transitions for water state {state}")
        for env in ("dry", "normal", "wet"):
            direct = direct_counts[(state, env)]
            direct_n = observed_context[(state, env)]
            if direct_n >= MIN_DIRECT_TRANSITIONS:
                counts = direct
                support = "derived"
                pooling = None
                provenance = f"Balanço hídrico diário derivado de NASA POWER e AWC SoilGrids/Saxton-Rawls; contexto {env}; n={direct_n}; spin-up 1981-1982 excluído. Não são transições de campo nem condicionadas a cultura/manejo."
            else:
                counts = pooled
                support = "pooled"
                pooling = "mesmo estado de água, agrupado entre seco/normal/úmido"
                provenance = f"Contagens derivadas agregadas por estado de água entre classes ambientais; contexto {env} tinha n={direct_n} (<{MIN_DIRECT_TRANSITIONS}); NASA POWER + SoilGrids/Saxton-Rawls; sem ação de cultura."
            transitions.append({
                "state": STATE_IDS[state], "action": ACTION, "environment": env,
                "counts": {STATE_IDS[destination]: int(counts[destination]) for destination in STATE_ORDER},
                "support": support, "provenance": provenance,
                "sample_size": int(direct_n), "effective_sample_size": int(sum(counts.values())),
                "pooling": pooling,
            })
    return dict(history), transitions, {"periods": period_values, "thresholds": {f"{m:02d}-{h+1}": {"p20_mm": p20, "p80_mm": p80} for (m,h),(p20,p80) in thresholds.items()}}


def write_climate_csv(path: Path, rows: list[dict]) -> None:
    fields = ["location_id", "date_local", "time_basis", "timezone", "source", "source_status", "precipitation_mm", "tmax_c", "tmin_c", "solar_mj_m2_day", "relative_humidity_pct", "wind_2m_ms", "eto_mm_day", "eto_method", "quality_valid", "quality_flags", "missing_variables"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            output = dict(row)
            output["date_local"] = row["_date"].isoformat()
            output["quality_flags"] = json.dumps(row["quality_flags"], ensure_ascii=False)
            output["missing_variables"] = json.dumps(row["missing_variables"], ensure_ascii=False)
            del output["_date"]
            writer.writerow(output)


def climate_summary(rows: list[dict], location_id: str) -> dict:
    training = [row for row in rows if row["_date"] <= TRAINING_LAST_DAY and row["quality_valid"]]
    valid_all = [row for row in rows if row["quality_valid"]]
    solar_all = [row for row in rows if row["solar_mj_m2_day"] is not None]
    years = defaultdict(list)
    for row in training:
        years[row["_date"].year].append(row)
    rainfall = [sum(row["precipitation_mm"] for row in values) for values in years.values()]
    eto_annual = [sum(row["eto_mm_day"] for row in values) for values in years.values()]
    return {
        "location_id": location_id,
        "available_daily_rows": len(rows),
        "latest_valid_climate_date": valid_all[-1]["_date"].isoformat(),
        "latest_solar_observation_date": solar_all[-1]["_date"].isoformat(),
        "training_first_date": training[0]["_date"].isoformat(),
        "training_last_date": training[-1]["_date"].isoformat(),
        "training_years": len(years),
        "radiation_missing_days": sum("solar_mj_m2_day" in row["missing_variables"] for row in training),
        "eto_hargreaves_days": sum("Hargreaves" in (row["eto_method"] or "") for row in training),
        "radiation_missing_days_all": sum("solar_mj_m2_day" in row["missing_variables"] for row in rows),
        "eto_hargreaves_days_all": sum("Hargreaves" in (row["eto_method"] or "") for row in rows),
        "mean_annual_precipitation_mm": mean(rainfall),
        "median_annual_precipitation_mm": quantile(rainfall, 0.5),
        "mean_annual_eto_mm": mean(eto_annual),
        "climate_quality": "NASA POWER PRECTOTCORR usado como chuva disponível neste perfil; relatório de pesquisa informa viés negativo de 14–18% frente a IMERG no Oeste do Paraná; não corrigido nem extrapolado para estes estados. RAD ausente nos 1.095 dias de 1981-1983 e em quatro dias do trecho recente; Hargreaves-Samani fornece ETo nesses dias. Última radiação observada 2026-11-03.",
    }


def profile_manifest(location: dict, raw_climate: Path, raw_soil: Path, climate_path: Path, soil_path: Path, transitions_path: Path, history_path: Path, states_path: Path, assumptions_path: Path, summary_path: Path, derivation_path: Path) -> dict:
    datasets = {
        "climate-daily.csv": {"origem": "NASA POWER Daily API v2.10.3", "responsavel": "NASA Langley Research Center", "frequencia": "diária, horário padrão local solar (LST)", "unidade": "mm/d; °C; MJ/m²/d; %; m/s", "periodo": f"1981-01-01 a {LAST_DAY.isoformat()}", "resolucao": "ponto amostrado no centroide municipal; grade nativa POWER, variável dependente", "qualidade": "T2M/chuva/humidade/vento; radiação ausente em 1981-1983 e em quatro dias recentes usa Hargreaves-Samani para ET0; chuva POWER sem correção contra IMERG", "sha256": sha256(climate_path), "contract_id": "climate_daily"},
        "soil-profile.json": {"origem": "ISRIC SoilGrids v2.0; AWC derivada por Saxton & Rawls (2006)", "responsavel": "ISRIC / Field Shift derivação", "frequencia": "perfil estático; predição média", "unidade": "%; g/kg; pH; mm de água disponível", "periodo": "mapa estático consultado em 2026-11-13", "resolucao": "célula SoilGrids 250 m no centroide IBGE municipal", "qualidade": "estimativa mapeada; AWC de pedotransfer; sem análise local", "sha256": sha256(soil_path), "contract_id": "soil_profile"},
        "states.json": {"origem": "classes 1/3 e 2/3 do plano MVP aplicadas ao balanço de referência", "responsavel": "Field Shift derivação", "frequencia": "estado de água por quinzena", "unidade": "fração da AWC em 0-100 cm", "periodo": "estado discreto calculado com climatologia 1981-2025", "resolucao": "ponto de referência municipal; 15 dias", "qualidade": "estado hídrico derivado; solo/cultura não classificados", "sha256": sha256(states_path), "contract_id": "markov_state"},
        "transitions.json": {"origem": "transições do balanço hídrico de NASA POWER + SoilGrids/Saxton-Rawls", "responsavel": "Field Shift derivação", "frequencia": "quinzenal", "unidade": "contagens por água atual × ambiente × água seguinte", "periodo": "1983-01-01 a 2025-12-31; spin-up 1981-1982 descartado", "resolucao": "ponto municipal; classes ambientais por percentis de chuva quinzenal", "qualidade": "derivado de modelo de referência, não observado em talhão; linhas esparsas agrupadas e identificadas", "sha256": sha256(transitions_path), "contract_id": "markov_transition"},
        "environment.json": {"origem": "classes quinzenais de precipitação NASA POWER; limiares por mês/quinzena, P20/P80", "responsavel": "Field Shift derivação", "frequencia": "quinzenal; anos completos", "unidade": "classe seca/normal/úmida", "periodo": "1981-01-01 a 2025-12-31", "resolucao": "ponto municipal; 24 períodos por ano", "qualidade": "dados POWER e classes derivadas; blocos sazonais usados no Monte Carlo", "sha256": sha256(history_path)},
        "assumptions.json": {"origem": "regras e premissas declaradas no plano MVP e nesta ingestão", "responsavel": "Field Shift", "frequencia": "por execução", "unidade": "ver arquivo", "periodo": "aplicado à série 1981-2025", "resolucao": "perfil de referência municipal", "qualidade": "suposições explícitas; não substituir dados de talhão", "sha256": sha256(assumptions_path)},
        "climate-summary.json": {"origem": "agregação de climate-daily.csv", "responsavel": "Field Shift", "frequencia": "por perfil", "unidade": "mm/ano", "periodo": "anos completos 1981-2025", "resolucao": "ponto municipal", "qualidade": "estatística descritiva de dados ambientais NASA POWER", "sha256": sha256(summary_path)},
        "markov-derivation.json": {"origem": "climate-daily.csv + soil-profile.json", "responsavel": "Field Shift", "frequencia": "quinzenal", "unidade": "mm, fração da CAD e classes", "periodo": "1981-2025", "resolucao": "ponto municipal", "qualidade": "balanço de referência sem cultura; limitações descritas no arquivo", "sha256": sha256(derivation_path)},
    }
    manifest_path = climate_path.parent / "manifest.json"
    existing_manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    datasets = {**existing_manifest.get("datasets", {}), **datasets}
    raw_sources = {
        **existing_manifest.get("raw_sources", {}),
        "nasa_power_json": {"path": str(raw_climate.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(raw_climate), "query": f"https://power.larc.nasa.gov/api/temporal/daily/point?parameters=T2M_MAX,T2M_MIN,RH2M,WS2M,ALLSKY_SFC_SW_DWN,PRECTOTCORR&community=AG&longitude={location['lon']}&latitude={location['lat']}&start=19810101&end=20261106&format=JSON", "api_start": "19810101", "api_end": "20261106", "time_standard": "LST", "retrieved_at": "2026-11-13"},
        "soilgrids_json": {"path": str(raw_soil.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(raw_soil), "query": f"https://rest.isric.org/soilgrids/v2.0/properties/query?lon={location['lon']}&lat={location['lat']}&property=clay&property=sand&property=silt&property=phh2o&property=soc&depth=0-5cm&depth=5-15cm&depth=15-30cm&depth=30-60cm&depth=60-100cm&value=mean", "value": "mean", "depths": [f"{top}-{bottom}cm" for top, bottom in DEPTHS], "retrieved_at": "2026-11-13"},
        "ibge_malha_geojson": {"path": f"data/raw/ibge/ibge-malha-municipal-{location['ibge_code']}.geojson", "sha256": sha256(RAW_IBGE / f"ibge-malha-municipal-{location['ibge_code']}.geojson"), "query": f"https://servicodados.ibge.gov.br/api/v3/malhas/municipios/{location['ibge_code']}?formato=application/vnd.geo%2Bjson&qualidade=intermediaria", "retrieved_at": "2026-11-13"},
    }
    return {
        "profile": location["id"], "version": "1.0.0", "natureza": "mista",
        "contract_version": current_contract_version(), "contract_registry": "data/contracts/registry.json",
        "description": "Perfil municipal de demonstração com séries ambientais reais da NASA e mapas estimados de solo. O balanço de referência não representa cultura, manejo ou talhão observado.",
        "location": {"municipality": location["municipality"], "uf": location["uf"], "ibge_code": location["ibge_code"], "longitude": location["lon"], "latitude": location["lat"], "coordinate_basis": "centroide de área da malha municipal IBGE; perfil regional, não seleção de talhão"},
        "datasets": datasets,
        "raw_sources": raw_sources,
    }


def build_location(location: dict) -> dict:
    raw_climate = RAW_POWER / f"nasa-power-daily-{location['source_stem']}-1981-20261106.json"
    raw_soil = RAW_SOIL / f"soilgrids-v2-{location['source_stem']}-mean.json"
    longitude, latitude = ibge_area_centroid(location["ibge_code"])
    if abs(longitude - location["lon"]) > 1e-5 or abs(latitude - location["lat"]) > 1e-5:
        raise ValueError(f"Configured NASA/SoilGrids point does not match IBGE centroid for {location['id']}: {(longitude, latitude)}")
    location = {**location, "lon": longitude, "lat": latitude}
    profile = PROFILES / location["id"]
    profile.mkdir(parents=True, exist_ok=True)
    climate = power_rows(location)
    soil = soil_profile(location)
    for index, row in enumerate(climate, start=2):
        validate_contract("climate_daily", {
            "location_id": row["location_id"],
            "date_local": row["_date"].isoformat(),
            "time_basis": row["time_basis"],
            "timezone": row["timezone"],
            "source": row["source"],
            "source_status": row["source_status"],
            "precipitation_mm": row["precipitation_mm"],
            "tmax_c": row["tmax_c"],
            "tmin_c": row["tmin_c"],
            "solar_mj_m2_day": row["solar_mj_m2_day"],
            "relative_humidity_pct": row["relative_humidity_pct"],
            "wind_2m_ms": row["wind_2m_ms"],
            "eto_mm_day": row["eto_mm_day"],
            "eto_method": row["eto_method"],
            "quality": {"valid": row["quality_valid"], "flags": row["quality_flags"], "missing_variables": row["missing_variables"]},
        }, source=f"{location['id']}/climate-daily.csv linha {index}")
    validate_contract("soil_profile", soil, source=f"{location['id']}/soil-profile.json")
    climate_path = profile / "climate-daily.csv"
    soil_path = profile / "soil-profile.json"
    states_path = profile / "states.json"
    transitions_path = profile / "transitions.json"
    history_path = profile / "environment.json"
    assumptions_path = profile / "assumptions.json"
    existing_assumptions = json.loads(assumptions_path.read_text(encoding="utf-8")) if assumptions_path.exists() else {}
    write_climate_csv(climate_path, climate)
    write_json(soil_path, soil)

    state_records = [
        {"id": STATE_IDS[water], "crop": "demanda_et0_de_referencia", "phase": "balanco_hidrico_quinzenal", "water": water, "soil": "mapeado_sem_classificacao", "recent_crops": []}
        for water in STATE_ORDER
    ]
    history, transitions, markov_meta = climate_history(climate, soil["available_water_capacity_mm"])
    validate_contract("markov_state", state_records, source=f"{location['id']}/states.json")
    validate_contract("markov_transition", transitions, source=f"{location['id']}/transitions.json")
    write_json(states_path, state_records)
    write_json(transitions_path, transitions)
    write_json(history_path, history)
    write_json(profile / "markov-derivation.json", {
        "method": "Balanço hídrico diário de referência; armazenamento limitado à AWC; P=NASA POWER PRECTOTCORR; ET=ET0 calculada; chuva acima da AWC é descartada como excedente sem coeficiente de escoamento calibrado; infiltração, drenagem profunda e ascensão capilar não modeladas.",
        "water_state_thresholds": {"baixa": "SW/AWC <= 1/3", "media": "1/3 < SW/AWC <= 2/3", "alta": "SW/AWC > 2/3"},
        "initial_storage_fraction": 0.5, "spinup_excluded_years": [1981, 1982],
        "environment_classification": "Rain total per calendar half-month: dry at zero or below the month-half P20; wet above P80; normal otherwise. Thresholds are calculated from 1981-2025 local POWER history.",
        "environment_thresholds": markov_meta["thresholds"],
        "periods": markov_meta["periods"],
        "limitations": ["No crop coefficient or crop calendar; reference ET0 is the demand.", "Rain above AWC is discarded as an uncalibrated excess; no explicit runoff coefficient, infiltration capacity, deep drainage, irrigation, capillary rise, or measured initial soil water.", "SoilGrids centroid value may not represent farmland or a field.", "Transition rows are model-derived from climate and mapped soil, not field observations or crop-specific responses."],
    })
    assumptions = {
        "initial_storage_fraction": 0.5,
        "initial_storage_status": "assumption; no measured initial water at a field",
        "water_state_thresholds": {"low": "SW/AWC <= 1/3", "medium": "1/3 < SW/AWC <= 2/3", "high": "SW/AWC > 2/3"},
        "root_zone_depth_cm": 100,
        "water_demand": "ET0 (Kc=1) reference surface; no crop is represented",
        "rainfall": "NASA POWER PRECTOTCORR, no correction; do not splice with IMERG",
        "soil": "SoilGrids mean prediction; Saxton & Rawls 2006 equations for field capacity and wilting point; organic matter estimated as SOC*1.724",
        "burn_in": "1981-1982 climate used to spin up the water bucket; omitted from Markov counts",
        "transition_prior": f"Dirichlet pseudocount {PSEUDOCOUNT} per water destination; prior is model uncertainty and not data",
        "sparse_context": f"When environment-specific transition count is below {MIN_DIRECT_TRANSITIONS}, pool same current water state over dry/normal/wet contexts; record effective and direct sample counts.",
        "monte_carlo": {"steps": 120, "trajectories": 10000, "seed": 2026, "block_periods": 2, "sample_transition_parameters_per_trajectory": True},
        "not_available": ["field_observations", "crop-specific transition counts", "ZARC planting eligibility", "field-measured soil and initial water", "crop yield, prices, costs, and VPL"],
    }
    assumptions = {**existing_assumptions, **assumptions}
    assumptions["not_available"] = list(dict.fromkeys(
        [*existing_assumptions.get("not_available", []), *assumptions["not_available"]]
    ))
    assumptions["monte_carlo"] = {
        **existing_assumptions.get("monte_carlo", {}),
        **assumptions.get("monte_carlo", {}),
    }
    write_json(assumptions_path, assumptions)
    summary = climate_summary(climate, location["id"])
    summary_path = profile / "climate-summary.json"
    derivation_path = profile / "markov-derivation.json"
    write_json(summary_path, summary)
    metadata = profile_manifest(location, raw_climate, raw_soil, climate_path, soil_path, transitions_path, history_path, states_path, assumptions_path, summary_path, derivation_path)
    validate_contract("profile_manifest", metadata, source=f"{location['id']}/manifest.json")
    write_json(profile / "manifest.json", metadata)
    return {"location": location, "summary": summary, "awc_mm": soil["available_water_capacity_mm"], "soil": soil}


def main() -> None:
    catalog = []
    for location in LOCATIONS:
        catalog.append(build_location(location))
    write_json(DATA / "catalog" / "perfis-exemplo.json", {
        "purpose": "Perfis carregados para a demonstração real; pontos municipais ilustrativos, sem seleção de talhão.",
        "selection_seed": 2026,
        "selection_rule": "A visualização sorteia uma localidade disponível por UF; existe uma localidade disponível em cada UF nesta entrega.",
        "profiles": [{"profile": item["location"]["id"], "municipality": item["location"]["municipality"], "uf": item["location"]["uf"], "ibge_code": item["location"]["ibge_code"], "longitude": item["location"]["lon"], "latitude": item["location"]["lat"], "training_period": [item["summary"]["training_first_date"], item["summary"]["training_last_date"]], "daily_rows": item["summary"]["available_daily_rows"], "mean_annual_precipitation_mm": item["summary"]["mean_annual_precipitation_mm"], "mean_annual_eto_mm": item["summary"]["mean_annual_eto_mm"], "awc_0_100_cm_mm": item["awc_mm"]} for item in catalog],
        "limitations": ["Ponto de referência é centroide municipal e não representa talhão.", "Chuva usa POWER PRECTOTCORR, sem IMERG local; comparação do Oeste do PR não é extrapolada para outros estados.", "O balanço de referência não contém ação; matrizes de cultura são acrescentadas por pipeline separado e são derivadas de processo, não observadas em campo.", "PAM municipal não calibra resposta causal; custos e preços locais continuam necessários para VPL."],
    })
    print(json.dumps({"profiles": [{"id": x["location"]["id"], "daily_rows": x["summary"]["available_daily_rows"], "awc_mm": round(x["awc_mm"], 1), "mean_annual_precipitation_mm": round(x["summary"]["mean_annual_precipitation_mm"], 1), "mean_annual_eto_mm": round(x["summary"]["mean_annual_eto_mm"], 1)} for x in catalog]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
