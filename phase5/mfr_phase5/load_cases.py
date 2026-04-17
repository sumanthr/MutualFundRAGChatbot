from __future__ import annotations

import json
from importlib import resources
from pathlib import Path
from typing import Any


def load_cases(path: Path | None = None) -> list[dict[str, Any]]:
    if path is not None:
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        try:
            raw = resources.files("mfr_phase5").joinpath("cases.json").read_text(encoding="utf-8")
        except (FileNotFoundError, ModuleNotFoundError, TypeError, ValueError):
            raw = (Path(__file__).resolve().parent / "cases.json").read_text(encoding="utf-8")
        data = json.loads(raw)
    cases = data.get("cases")
    if not isinstance(cases, list):
        raise ValueError("cases.json: missing cases array")
    return cases
