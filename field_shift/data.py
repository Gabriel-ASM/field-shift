"""Load the structured data consumed by the first simulation core."""

import json
from pathlib import Path

from .markov import FieldState, MarkovModel, TransitionKey
from .monte_carlo import SeasonalHistory


def load_profile(directory: Path, *, pseudocount: float = 0.5) -> tuple[MarkovModel, SeasonalHistory]:
    manifest = _read(directory / "manifest.json")
    for filename in ("states.json", "transitions.json", "environment.json"):
        metadata = manifest["datasets"].get(filename, {})
        for field in ("origem", "responsavel", "frequencia"):
            if not isinstance(metadata.get(field), str) or not metadata[field].strip():
                raise ValueError(f"Missing {field!r} in manifest for {filename}")
    states = _read(directory / "states.json")
    transitions = _read(directory / "transitions.json")
    history = _read(directory / "environment.json")
    rows = {}
    for record in transitions:
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
        SeasonalHistory(history[str(year)] for year in sorted(map(int, history))),
    )


def _read(path: Path):
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)
