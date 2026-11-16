"""Assemble the profile of any municipality on demand, in a background thread, polled for progress.

Experimental: the data is fetched and derived by the scripts in data/pipeline and nobody reviews it. Up to
CONCURRENT municipalities are assembled at a time and the others wait their turn. Their downloads run side by
side (each writes its own files); the derivation, which rewrites the catalog and the shared references, runs for
one municipality at a time. Stages:

    crop history (IBGE PAM)  ->  planting windows (MAPA ZARC)  ->  weather (NASA POWER)  ->  soil (SoilGrids)
    ->  water balance  ->  crops  ->  crop transitions  ->  prices and costs  ->  simulation documents
"""

from __future__ import annotations

import gzip
import json
import subprocess
import sys
import threading
import uuid
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Callable

from pymongo.database import Database

from .. import DATA, ROOT
from ..contracts import check, validate
from ..db import upsert

PIPELINE = DATA / "pipeline"
CATALOG = DATA / "catalog" / "perfis-exemplo.json"
KEPT = 50       # finished builds remembered, so a page that reloads can still read how one ended
CONCURRENT = 3  # municipalities assembled at the same time


@dataclass
class Stage:
    label: str
    weight: float                       # share of the progress bar, about its share of the time
    commands: Callable[[dict], list[list[str]]]
    shared: bool = False                # rewrites files of every profile: one municipality at a time


def _script(name: str, *arguments: str) -> list[str]:
    return [sys.executable, str(PIPELINE / name), *arguments]


STAGES = [
    Stage("Crop history · IBGE PAM", 2, lambda m: [_script("fetch_pam_targets.py", "--codes", m["code"])]),
    Stage("Planting windows · MAPA ZARC", 1, lambda m: [_script("fetch_zarc_national.py")], shared=True),
    Stage("Weather since 1981 · NASA POWER", 6, lambda m: [_script("fetch_power.py", "--codes", m["code"])]),
    Stage("Soil · ISRIC SoilGrids", 30, lambda m: [_script("fetch_soil.py", "--codes", m["code"], "--pause", "3")]),
    Stage("Water balance of the soil", 4, lambda m: [_script("build_profiles.py", "--codes", m["code"], "--append")], shared=True),
    Stage("Crops and planting calendar", 5, lambda m: [_script("prepare_crop_data.py", "--profiles", m["id"])], shared=True),
    Stage("Crop transitions", 6, lambda m: [_script("build_crop_markov.py", "--profiles", m["id"]),
                                             _script("build_crop_transition_markov.py", "--profiles", m["id"])], shared=True),
    Stage("Prices and costs · CONAB", 6, lambda m: [_script("build_economic_benchmarks.py")], shared=True),
]
INGEST = Stage("Simulation documents", 1, lambda m: [])
TOTAL = sum(stage.weight for stage in [*STAGES, INGEST])


@dataclass
class Build:
    id: str
    municipality: dict                  # {code, name, uf, id, lon, lat}
    status: str = "queued"              # queued, running, done, failed
    stage: str = "Waiting for a free place in the queue"
    fraction: float = 0.0
    error: str | None = None

    def view(self) -> dict[str, Any]:
        return {"id": self.id, "status": self.status, "stage": self.stage, "fraction": round(self.fraction, 3),
                "error": self.error, "profile": self.municipality["id"],
                "municipality": {key: self.municipality[key] for key in ("code", "name", "uf")}}


@lru_cache(maxsize=1)
def _municipalities() -> dict[str, dict]:
    """Every municipality by IBGE code; read once, it takes a second or two (5,570 boundaries)."""
    if str(PIPELINE) not in sys.path:
        sys.path.insert(0, str(PIPELINE))
    import targets
    return targets.municipalities()


def municipality(code: str) -> dict | None:
    """The municipality of an IBGE code, with the profile id it gets; None when IBGE has no boundary for it."""
    return _municipalities().get(code)


def harvested_years(code: str) -> int:
    """Years in which IBGE PAM records a harvested area of any modelled crop in the municipality."""
    path = DATA / "raw" / "ibge" / "pam" / f"{code}.json.gz"
    years = set()
    for row in json.loads(gzip.decompress(path.read_bytes()))["records"]:
        if str(row.get("D2C")) == "216" and str(row.get("V", "")).replace(".", "", 1).isdigit() and float(row["V"]) > 0:
            years.add(row["D3C"])
    return len(years)


def forget(profile_id: str) -> None:
    """Take a profile that could not be completed out of the catalog, so nothing later expects its files."""
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    kept = [entry for entry in catalog["profiles"] if entry["profile"] != profile_id]
    if len(kept) != len(catalog["profiles"]):
        CATALOG.write_text(json.dumps({**catalog, "profiles": kept}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def in_catalog(profile_id: str) -> bool:
    return any(entry["profile"] == profile_id for entry in json.loads(CATALOG.read_text(encoding="utf-8"))["profiles"])


class Builds:
    def __init__(self) -> None:
        self._builds: dict[str, Build] = {}
        self._lock = threading.Lock()                       # guards the dictionary
        self._places = threading.Semaphore(CONCURRENT)      # municipalities being assembled
        self._zarc = threading.Lock()                       # the national tables are downloaded once
        self._derive = threading.Lock()                     # the scripts that rewrite shared files

    def get(self, build_id: str) -> Build | None:
        return self._builds.get(build_id)

    def start(self, target: dict, database: Database) -> Build:
        """Start assembling a municipality, or return the build of it that is already under way."""
        with self._lock:
            for build in self._builds.values():
                if build.municipality["code"] == target["code"] and build.status in ("queued", "running"):
                    return build
            build = Build(uuid.uuid4().hex[:12], target)
            self._builds[build.id] = build
            for old in [key for key, item in self._builds.items() if item.status in ("done", "failed")][:-KEPT]:
                del self._builds[old]
        threading.Thread(target=self._run, args=(build, database), daemon=True).start()
        return build

    def _run(self, build: Build, database: Database) -> None:
        zarc = STAGES[1]
        with self._places:
            build.status = "running"
            try:
                done = 0.0
                for stage in [stage for stage in STAGES if stage is zarc or not stage.shared]:
                    if stage is zarc:       # whoever arrives second finds the national tables stored
                        with self._zarc:
                            done = self._stage(build, stage, done)
                    else:
                        done = self._stage(build, stage, done)
                    if stage is STAGES[0] and harvested_years(build.municipality["code"]) < 2:
                        # Known in a second, before the slow downloads: the crop transitions come from this history.
                        raise RuntimeError("IBGE records no harvest of the modelled crops (soybean, maize, sugarcane, coffee…) "
                                           f"in {build.municipality['name']}.")
                # From the catalog entry to the documents in one piece: a script that reads every profile of the
                # catalog must not find one that another municipality has only half derived.
                build.stage = "Waiting for another municipality to be derived"
                with self._derive:
                    try:
                        for stage in [stage for stage in STAGES if stage.shared and stage is not zarc]:
                            done = self._stage(build, stage, done)
                        build.stage = INGEST.label
                        ingest(build.municipality["id"], database)
                    except Exception:
                        forget(build.municipality["id"])
                        raise
                build.fraction, build.status, build.stage = 1.0, "done", "Ready"
            except Exception as failure:        # the page shows the reason; the thread must not die silently
                build.status, build.error = "failed", str(failure)

    def _stage(self, build: Build, stage: Stage, done: float) -> float:
        build.stage = stage.label
        commands = stage.commands(build.municipality)
        for index, command in enumerate(commands):
            base = done + stage.weight * index / len(commands)
            self._execute(command, lambda share, base=base, span=stage.weight / len(commands):
                          setattr(build, "fraction", (base + span * share) / TOTAL))
        build.fraction = (done + stage.weight) / TOTAL
        return done + stage.weight

    @staticmethod
    def _execute(command: list[str], progress: Callable[[float], None]) -> None:
        """Run one pipeline script; its "progress <0-1>" lines move the bar, a SKIP or FAIL line is the failure."""
        process = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        tail: list[str] = []
        problem = None
        assert process.stdout is not None
        for line in process.stdout:
            line = line.rstrip()
            if line.startswith("progress "):
                try:
                    progress(float(line.split()[1]))
                except ValueError:
                    pass
                continue
            if line.startswith(("SKIP ", "FAIL ")):
                problem = line[5:]
            tail = [*tail, line][-6:]
        if process.wait() != 0 or problem:
            raise RuntimeError(problem or "\n".join(tail) or f"{command[1]} failed")


def ingest(profile_id: str, database: Database) -> None:
    """Build the chain and the profile document of one profile, store them in data/v2 and in the database."""
    from ..ingest import build_chain, build_profile
    if not in_catalog(profile_id):
        raise RuntimeError("the profile was not assembled")
    chain, _ = build_chain(profile_id)
    document = build_profile(profile_id, chain["initial_state"])
    for name, payload in (("markov", chain), ("profile", document)):
        errors = validate(name, payload) or check(name, payload)
        if errors:
            raise RuntimeError(f"{name} of {profile_id} violates its contract: " + "; ".join(errors[:3]))
    for kind, payload in (("chains", chain), ("profiles", document)):
        path = DATA / "v2" / kind / f"{profile_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        upsert(database, kind, payload)
