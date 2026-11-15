"""Planting calendar in decendios (three per month, 36 per year) over a 365-day year."""

from __future__ import annotations

import re

import numpy as np

DAYS_PER_YEAR = 365
MONTH_DAYS = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
INTERCROP = re.compile("consorciad|consórcio|mistura", re.IGNORECASE)


def decendio_of_day(day: int) -> int:
    """Decendio (1-36) of a day counted from January 1st; the third one takes the rest of the month."""
    remaining = day % DAYS_PER_YEAR
    for month, length in enumerate(MONTH_DAYS):
        if remaining < length:
            return month * 3 + min(remaining // 10, 2) + 1
        remaining -= length
    return 36


DECENDIO_BY_DAY = np.array([decendio_of_day(day) for day in range(DAYS_PER_YEAR)])


def official_windows(rows: list[dict], crops: set[str], risk_levels: list[int]) -> dict[str, set[int]]:
    """Decendios published by MAPA ZARC per crop. A crop listed with no decendio keeps an empty set."""
    windows: dict[str, set[int]] = {}
    for row in rows:
        crop = row.get("crop_parameter_id")
        if crop not in crops or INTERCROP.search(str(row.get("crop") or "")):
            continue
        published = row.get("planting_decendios_by_risk_percent") or {}
        windows.setdefault(crop, set()).update(
            int(decendio) for risk in risk_levels for decendio in published.get(str(risk), []))
    return windows


def lowest_risk(rows: list[dict], crops: set[str], risk_levels: list[int]) -> dict[str, dict[int, int]]:
    """Per crop and decendio, the lowest ZARC risk (%) any published row gives, over the same rows as the engine."""
    risk: dict[str, dict[int, int]] = {}
    for row in rows:
        crop = row.get("crop_parameter_id")
        if crop not in crops or INTERCROP.search(str(row.get("crop") or "")):
            continue
        published = row.get("planting_decendios_by_risk_percent") or {}
        for level in risk_levels:
            for decendio in published.get(str(level), []):
                current = risk.setdefault(crop, {}).get(int(decendio))
                risk[crop][int(decendio)] = level if current is None else min(current, level)
    return risk


def planting_windows(rows: list[dict], crops: list[str], crop_cycles: dict) -> dict[str, set[int]]:
    """Official windows, plus the all-year fallback for listed rotation covers without an official row."""
    risk_levels = crop_cycles["time_basis"]["planting_calendar"]["risk_levels_included_percent"]
    windows = official_windows(rows, set(crops), risk_levels)
    fallback = crop_cycles.get("rotation_calendar_fallback") or {}
    for crop in fallback.get("crop_ids", []):
        if crop in crops and crop not in windows:
            windows[crop] = set(fallback.get("all_year_decendios", []))
    return windows


def days_until_open(decendios: set[int]) -> np.ndarray:
    """For each day of the year, days to wait until a day inside one of `decendios`; inf if there is none."""
    wait = np.full(DAYS_PER_YEAR, np.inf)
    if not decendios:
        return wait
    is_open = np.isin(DECENDIO_BY_DAY, list(decendios))
    for day in range(2 * DAYS_PER_YEAR - 1, -1, -1):
        today = day % DAYS_PER_YEAR
        wait[today] = 0 if is_open[today] else wait[(today + 1) % DAYS_PER_YEAR] + 1
    return wait
