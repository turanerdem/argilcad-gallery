#!/usr/bin/env python3
"""Build a gallery model and print what it measures.

    python tools/runtime.py models/<slug>/model.py

A gallery model is a plain build123d script: it imports what it uses and
assigns the finished shape (or builder) to `result`. It runs here as an
ordinary Python script, with build123d and bd_warehouse installed from
tools/requirements.txt and nothing else, so it runs the same anywhere.

Prints one JSON object: {"metrics": {...}, "build_ms": n}, or
{"error": "...", "traceback": "..."} with exit status 1.
"""
from __future__ import annotations

import json
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Dict


def resolve(result: Any) -> Any:
    """`result` → a shape: a builder gives its part, a shape is itself."""
    if hasattr(result, "part") and not hasattr(result, "wrapped"):
        result = result.part
    if not hasattr(result, "wrapped"):
        raise TypeError(f"'result' must be a build123d shape or builder, not {type(result).__name__}")
    return result


def measure(shape: Any) -> Dict[str, Any]:
    """Bounding box, volume, area and topology counts, in mm, to 3 decimals.
    Volume adds up every solid, nested assemblies included."""
    size = shape.bounding_box().size
    solids = shape.solids()
    volume = sum(s.volume for s in solids) if solids else shape.volume
    return {
        "bbox": [round(size.X, 3), round(size.Y, 3), round(size.Z, 3)],
        "volume": round(float(volume), 3),
        "area": round(float(shape.area), 3),
        "face_count": len(shape.faces()),
        "edge_count": len(shape.edges()),
        "vertex_count": len(shape.vertices()),
    }


def run(path: Path) -> Dict[str, Any]:
    code = path.read_text(encoding="utf-8")
    namespace: Dict[str, Any] = {"__name__": "__gallery__", "__file__": str(path)}
    started = time.monotonic()
    exec(compile(code, str(path), "exec"), namespace)
    if "result" not in namespace:
        raise NameError("the script must assign the finished model to `result`")
    shape = resolve(namespace["result"])
    return {"metrics": measure(shape), "build_ms": int((time.monotonic() - started) * 1000)}


def main(argv) -> int:
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        print(json.dumps(run(Path(argv[1]))))
        return 0
    except Exception as exc:  # the script's own failure, reported as data
        print(json.dumps({"error": f"{type(exc).__name__}: {exc}",
                          "traceback": traceback.format_exc(limit=-3)}))
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
