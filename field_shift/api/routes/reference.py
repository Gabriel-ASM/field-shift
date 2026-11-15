"""Development only: browse the team's source material (research notes, downloads, earlier pages, raw data).

Enabled when FIELD_SHIFT_REFERENCE_DIR points to a folder; the development image sets it to a copy of the repository.
"""

from __future__ import annotations

import html
import os
from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

FILES_PATH = "/reference/files"
MAX_LISTED = 5000
PAGE = """<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Field Shift reference</title>
<style>body{{font:15px/1.5 system-ui,sans-serif;max-width:920px;margin:24px auto;padding:0 16px;color-scheme:light dark}}
h2{{font-size:1rem;margin:24px 0 4px}}ul{{margin:0;padding-left:18px}}small{{opacity:.6}}</style>
<h1>Field Shift reference</h1><p>The repository as it was when this development image was built. Not part of the product.</p>{sections}"""


def reference_dir() -> Path | None:
    configured = os.environ.get("FIELD_SHIFT_REFERENCE_DIR")
    return Path(configured) if configured and Path(configured).is_dir() else None


def listed_files(root: Path) -> list[Path]:
    """Files under `root`, relative to it, in a stable order."""
    return sorted(path.relative_to(root) for path in root.rglob("*") if path.is_file())[:MAX_LISTED]


def group_by_folder(files: list[Path]) -> dict[str, list[Path]]:
    groups: dict[str, list[Path]] = {}
    for path in files:
        groups.setdefault(path.parts[0] if len(path.parts) > 1 else "(root)", []).append(path)
    return groups


def section(folder: str, files: list[Path], root: Path) -> str:
    items = "".join(
        f'<li><a href="{FILES_PATH}/{html.escape(path.as_posix(), quote=True)}">{html.escape(path.as_posix())}</a>'
        f" <small>{(root / path).stat().st_size // 1024} KiB</small></li>" for path in files)
    return f"<h2>{html.escape(folder)} ({len(files)})</h2><ul>{items}</ul>"


def index_page(root: Path) -> str:
    groups = group_by_folder(listed_files(root))
    return PAGE.format(sections="".join(section(folder, files, root) for folder, files in groups.items()))


def install(app: FastAPI) -> None:
    """Add /reference to the app when a reference folder is configured; otherwise do nothing."""
    root = reference_dir()
    if root is None:
        return
    router = APIRouter(tags=["reference"])

    @router.get("/reference", response_class=HTMLResponse)
    def reference_index() -> str:
        return index_page(root)

    app.include_router(router)
    app.mount(FILES_PATH, StaticFiles(directory=root), name="reference")
