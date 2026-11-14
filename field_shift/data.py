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


def _read(path: Path):
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)
