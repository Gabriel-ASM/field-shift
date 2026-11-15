"""Load the structured data consumed by the first simulation core."""

import json
from pathlib import Path

from .markov import FieldState, MarkovModel, TransitionKey
from .monte_carlo import SeasonalHistory


def load_profile(directory: Path, *, pseudocount: float = 0.5) -> tuple[MarkovModel, SeasonalHistory]:
    manifest = _read(directory / "manifest.json")
    if manifest.get("natureza") not in {"observada", "derivada", "mista"}:
        raise ValueError("Manifest nature must identify observed, derived or mixed data")
    for filename in ("states.json", "transitions.json", "environment.json"):
        metadata = manifest["datasets"].get(filename, {})
        for field in ("origem", "responsavel", "frequencia", "unidade", "periodo", "resolucao", "qualidade"):
            if not isinstance(metadata.get(field), str) or not metadata[field].strip():
                raise ValueError(f"Missing {field!r} in manifest for {filename}")
    if "assumptions.json" in manifest["datasets"]:
        metadata = manifest["datasets"]["assumptions.json"]
        for field in ("origem", "responsavel", "frequencia", "unidade", "periodo", "resolucao", "qualidade"):
            if not isinstance(metadata.get(field), str) or not metadata[field].strip():
                raise ValueError(f"Missing {field!r} in manifest for assumptions.json")
    states = _read(directory / "states.json")
    transitions = _read(directory / "transitions.json")
    history = _read(directory / "environment.json")
    seasonal_history = SeasonalHistory(history[str(year)] for year in sorted(map(int, history)))
    environment_labels = {label for year in history.values() for label in year}
    rows = {}
    for record in transitions:
        if record.get("environment") not in environment_labels:
            raise ValueError(f"Transition environment is absent from environment history: {record.get('environment')!r}")
        if record.get("support") not in {"observed", "derived", "pooled", "prior"}:
            raise ValueError("Each transition row must declare observed, derived, pooled or prior support")
        if not isinstance(record.get("provenance"), str) or not record["provenance"].strip():
            raise ValueError("Each transition row must identify its source or prior")
        key = TransitionKey(record["state"], record["action"], record["environment"])
        if key in rows:
            raise ValueError(f"Duplicate transition row: {key}")
        rows[key] = record["counts"]
    return (
        MarkovModel(
            [
                FieldState(**{**record, "recent_crops": tuple(record.get("recent_crops", ()))})
                for record in states
            ],
            rows,
            pseudocount=pseudocount,
        ),
        seasonal_history,
    )


def load_crop_scenario(
    directory: Path,
    crop_parameter_id: str,
    planting_decendio: int,
    *,
    pseudocount: float = 0.5,
) -> tuple[MarkovModel, SeasonalHistory, dict]:
    """Load a ZARC-eligible crop/planting-window water model for Monte Carlo.

    Rows remain process-derived, not observed treatment effects. The 0.5 prior
    is applied by MarkovModel only to destinations present in the row counts.
    """
    _, history = load_profile(directory, pseudocount=pseudocount)
    manifest = _read(directory / "manifest.json")
    metadata = manifest["datasets"].get("crop-markov-scenarios.json", {})
    for field in ("origem", "responsavel", "frequencia", "unidade", "periodo", "resolucao", "qualidade"):
        if not isinstance(metadata.get(field), str) or not metadata[field].strip():
            raise ValueError(f"Missing {field!r} in manifest for crop-markov-scenarios.json")
    payload = _read(directory / "crop-markov-scenarios.json")
    scenario = next((
        row for row in payload["scenarios"]
        if row["crop_parameter_id"] == crop_parameter_id
        and row["planting_decendio"] == planting_decendio
    ), None)
    if scenario is None:
        raise ValueError(
            f"No ZARC-eligible crop scenario for {crop_parameter_id!r}, decendio {planting_decendio}"
        )
    environment_labels = {label for year in history._years for label in year}
    states = {
        row["id"]: FieldState(
            id=row["id"], crop=row["crop"], phase=row["phase"], water=row["water"],
            soil="mapeado_sem_classificacao", recent_crops=(),
        )
        for row in scenario["states"]
    }
    transitions = {}
    action = scenario["action"]
    for row in scenario["transitions"]:
        if row["action"] != action:
            raise ValueError("Crop scenario contains mixed actions")
        if row["environment"] not in environment_labels:
            raise ValueError(f"Crop transition environment is absent from history: {row['environment']!r}")
        if row.get("support") not in {"derived", "pooled"}:
            raise ValueError("Crop transition support must be derived or pooled")
        if not isinstance(row.get("provenance"), str) or not row["provenance"].strip():
            raise ValueError("Each crop transition row must declare its derivation")
        key = TransitionKey(row["state"], action, row["environment"])
        if key in transitions:
            raise ValueError(f"Duplicate crop transition row: {key}")
        transitions[key] = row["counts"]
    if scenario["initial_state_id"] not in states:
        raise ValueError("Crop scenario initial state is absent from state metadata")
    if not any(key.state == scenario["initial_state_id"] for key in transitions):
        raise ValueError("Crop scenario initial state has no outgoing transition rows")
    model = MarkovModel(list(states.values()), transitions, pseudocount=pseudocount)
    return model, history, scenario


def _read(path: Path):
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)
