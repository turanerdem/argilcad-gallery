#!/usr/bin/env python3
"""The gallery's own tooling: generate the derived files, and check entries.

    python tools/gallery.py generate              index.jsonl, READMEs, REUSE.toml
    python tools/gallery.py check                 every entry, built and measured
    python tools/gallery.py check --only <slug>   one entry
    python tools/gallery.py check --no-build      everything but the build
    python tools/gallery.py check --changed origin/main
    python tools/gallery.py reverify              build every entry, report drift

Nothing here writes into models/<slug>/ except that folder's README.md, which
is generated. meta.json and the media come from Argil Design's publishing
tool; model.py is the source of truth for everything else.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "models"
SCHEMA = ROOT / "schema" / "meta.schema.json"
INDEX = ROOT / "index.jsonl"
README = ROOT / "README.md"
REUSE = ROOT / "REUSE.toml"
RUNTIME = ROOT / "tools" / "runtime.py"
LICENSES = ROOT / "LICENSES"
LICENSE_STORE = ROOT / "tools" / "licenses"

REPO_SLUG = "turanerdem/argilcad-gallery"
CDN = f"https://cdn.jsdelivr.net/gh/{REPO_SLUG}@main"
APP_URL = "https://argildesign.com/argilcad/"
SITE_URL = "https://argildesign.com/products/argilcad/"
OWNER_COPYRIGHT = "2026 Argil Design"

LICENSE_NAMES = {
    "CC-BY-NC-SA-4.0": ("CC BY-NC-SA 4.0", "https://creativecommons.org/licenses/by-nc-sa/4.0/"),
    "CC-BY-NC-4.0": ("CC BY-NC 4.0", "https://creativecommons.org/licenses/by-nc/4.0/"),
    "CC-BY-SA-4.0": ("CC BY-SA 4.0", "https://creativecommons.org/licenses/by-sa/4.0/"),
    "CC-BY-4.0": ("CC BY 4.0", "https://creativecommons.org/licenses/by/4.0/"),
}
SOURCE_NAMES = {
    "app_llm": "ArgilCAD's AI",
    "mcp": "an AI assistant over MCP",
    "own_ai": "the user's own AI",
    "hand": "hand-written code",
    "tool": "ArgilCAD's modelling tools",
    "mixed": "AI and hand edits",
}

# Ceilings per file (bytes) and the pixel size each kind must have.
MAX_BYTES = {
    "model": 5 * 1024 * 1024,
    "turntable": 1024 * 1024,
    "animation": 1024 * 1024,
    "view": 300 * 1024,
    "thumb": 100 * 1024,
    "og": 250 * 1024,
}
MAX_CODE_BYTES = 200 * 1024
NON_ENGLISH_LETTERS = re.compile(r"[çğıöşüÇĞİÖŞÜâîû]")
REQUIRED_VIEWS = ("iso", "front", "top", "right")

# Volume and area must agree to this; topology counts exactly. The app and
# this runtime run the same OCCT; this leaves room for the rounding at three
# decimals only.
METRIC_REL_TOL = 1e-6
METRIC_ABS_TOL = 0.0015
BUILD_TIMEOUT_S = 300

# Content policy (CONTRIBUTING.md). Matched as whole words, case-insensitive,
# in the title, summary, tags and prompt.
FORBIDDEN_WORDS = (
    "gun", "guns", "firearm", "firearms", "rifle", "pistol", "handgun", "receiver",
    "suppressor", "silencer", "ammunition", "ammo", "bullet", "grenade", "explosive",
    "bomb", "weapon", "weapons",
    "silah", "tabanca", "tüfek", "susturucu", "mermi", "fişek", "bomba", "patlayıcı",
)
BRAND_WORDS = (
    "thrustmaster", "th8s", "akıncı", "akinci", "bayraktar", "baykar", "tb2", "tb3",
    "lego", "disney", "marvel", "nintendo", "pokemon", "pokémon", "star wars",
    "apple", "iphone", "tesla", "ferrari", "porsche", "ikea",
)
PII_PATTERNS = (
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "an e-mail address"),
    (re.compile(r"(?<!\d)\+?\d[\d \-()]{8,}\d(?!\d)"), "a phone number"),
)


# ------------------------------------------------------------------ loading

def entries() -> List[Tuple[Path, Dict[str, Any]]]:
    out = []
    for meta in sorted(MODELS.glob("*/meta.json")):
        out.append((meta.parent, json.loads(meta.read_text(encoding="utf-8"))))
    return out


def withdrawn_ids() -> set:
    path = ROOT / "withdrawn.jsonl"
    if not path.exists():
        return set()
    return {json.loads(line)["id"] for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}


# The publishing tool fingerprints a model with these same two functions:
# a fingerprint taken there must equal the one taken here.

_INJECTED_MODULES = re.compile(
    r"^(build123d|math|numpy|random|itertools|functools|collections|bd_warehouse)(\.|$)")


def _injected_import(node: ast.stmt) -> bool:
    if isinstance(node, ast.ImportFrom):
        return bool(node.module and _INJECTED_MODULES.match(node.module))
    if isinstance(node, ast.Import):
        return all(_INJECTED_MODULES.match(a.name) for a in node.names)
    return False


def code_fingerprint(code: str) -> str:
    tree = ast.parse(code)
    tree.body = [n for n in tree.body if not _injected_import(n)] or [ast.Pass()]
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if isinstance(body, list) and body and isinstance(body[0], ast.Expr) \
                and isinstance(getattr(body[0], "value", None), ast.Constant) \
                and isinstance(body[0].value.value, str):
            node.body = body[1:] or [ast.Pass()]
    return hashlib.sha256(ast.unparse(tree).encode("utf-8")).hexdigest()


def geom_fingerprint(m: Dict[str, Any]) -> List[float]:
    dims = sorted(float(x) for x in m["bbox"])
    big = dims[2] or 1.0
    box = (dims[0] or 1e-9) * (dims[1] or 1e-9) * big
    vol = abs(float(m["volume"])) or 1e-9
    return [
        round(dims[0] / big, 4),
        round(dims[1] / big, 4),
        round(min(vol / box, 1.0), 4),
        round(float(m["area"]) / (vol ** (2.0 / 3.0)), 4),
        round(math.log1p(int(m["face_count"])), 4),
        round(math.log1p(len(m.get("parts") or [])), 4),
    ]


# --------------------------------------------------------------- generating

def _media(meta: Dict[str, Any], kind: str, view: Optional[str] = None) -> Optional[str]:
    for m in meta["media"]:
        if m["kind"] == kind and (view is None or m.get("view") == view):
            return m["file"]
    return None


def index_lines(items) -> List[str]:
    rows = []
    for folder, meta in items:
        base = f"models/{meta['slug']}"
        files = {
            "code": f"{base}/model.py",
            "meta": f"{base}/meta.json",
        }
        for kind in ("model", "thumb", "og", "turntable", "animation"):
            f = _media(meta, kind)
            if f:
                files["glb" if kind == "model" else kind] = f"{base}/{f}"
        files["views"] = {
            m["view"]: f"{base}/{m['file']}" for m in meta["media"] if m["kind"] == "view"
        }
        rows.append({
            "id": meta["id"],
            "slug": meta["slug"],
            "title": meta["title"],
            "summary": meta["summary"],
            "tags": meta["tags"],
            "category": meta["category"],
            "license": meta["license"],
            "ai_training": meta["ai_training"],
            "author": meta["author"]["display"],
            "source": meta["source"]["kind"],
            "derived_from": meta["derived_from"],
            "created": meta["created"],
            "bbox": meta["metrics"]["bbox"],
            "volume": meta["metrics"]["volume"],
            "parts": len(meta["metrics"]["parts"]),
            "files": files,
        })
    rows.sort(key=lambda r: (r["created"], r["slug"]), reverse=True)
    return [json.dumps(r, ensure_ascii=False, sort_keys=True) for r in rows]


def _size(bbox) -> str:
    return " × ".join(f"{x:g}" for x in (round(v, 1) for v in bbox)) + " mm"


def _volume(mm3: float) -> str:
    return f"{mm3 / 1000:.1f} cm³"


def _license_link(spdx: str) -> str:
    name, url = LICENSE_NAMES[spdx]
    return f"[{name}]({url})"


def model_readme(meta: Dict[str, Any]) -> str:
    t, s = meta["title"], meta["summary"]
    m = meta["metrics"]
    lines = [
        "<!-- Generated by tools/gallery.py from meta.json. Do not edit. -->",
        f"# {t['en']}",
        "",
    ]
    motion = _media(meta, "animation") or _media(meta, "turntable")
    if motion:
        lines += [f'<img src="{motion}" width="360" alt="{t["en"]}">', ""]
    lines += [s["en"], "", f"> **{t['tr']}** — {s['tr']}", ""]

    views = [m_ for m_ in meta["media"] if m_["kind"] == "view"]
    if views:
        lines += ["| " + " | ".join(v["view"] for v in views) + " |",
                  "|" + "---|" * len(views),
                  "| " + " | ".join(f'<img src="{v["file"]}" width="160" alt="{v["view"]}">' for v in views) + " |",
                  ""]

    rows = [
        ("Size", _size(m["bbox"])),
        ("Volume", _volume(m["volume"])),
        ("Parts", str(len(m["parts"])) if m["parts"] else "1"),
    ]
    p = meta.get("print") or {}
    if p.get("printed"):
        printed = "yes"
        if p.get("grams"):
            printed += f", {p['grams']:g} g"
        if p.get("print_in_place"):
            printed += ", print-in-place"
        rows.append(("Printed", printed))
    src = meta["source"]
    made = SOURCE_NAMES[src["kind"]]
    if src.get("client"):
        made += f" ({src['client']})"
    rows += [
        ("Made with", made),
        ("Author", meta["author"]["display"]),
        ("License", _license_link(meta["license"])),
        ("Engine", f"build123d {meta['engine'].get('build123d', '?')}, OCCT {meta['engine'].get('ocp', '?')}"),
        ("Added", meta["created"]),
        ("ID", f"`{meta['id']}`"),
    ]
    if meta.get("derived_from"):
        rows.append(("Remix of", f"`{meta['derived_from']}`"))
    lines += ["| | |", "|---|---|"] + [f"| {k} | {v} |" for k, v in rows] + [""]

    lines += [
        "## Use it",
        "",
        f"- **Code:** [`model.py`](model.py) — paste it into the code editor of "
        f"[ArgilCAD]({APP_URL}) and run it, then change anything.",
        "- **3D:** [`model.glb`](model.glb)",
        "- **Outside the app:** `python tools/runtime.py "
        f"models/{meta['slug']}/model.py` from the gallery's root builds it with plain build123d.",
        "",
    ]
    if p.get("notes"):
        lines += [f"**Printing:** {p['notes']}", ""]
    if meta.get("params"):
        lines += ["## Parameters", "", "| Name | Default | Range | Unit |", "|---|---|---|---|"]
        for prm in meta["params"]:
            rng = f"{prm.get('min', '')} – {prm.get('max', '')}" if "min" in prm or "max" in prm else ""
            lines.append(f"| `{prm['name']}` | {prm['default']} | {rng} | {prm.get('unit', '')} |")
        lines.append("")
    if meta.get("prompt"):
        lines += ["## Prompt", "", "```text", meta["prompt"]["text"], "```", ""]
    lines += [
        "---",
        f"© {meta['copyright']} · {_license_link(meta['license'])} · "
        "AI training on this gallery is welcome; the licence still applies to copies of the model.",
        "",
    ]
    return "\n".join(lines)


def root_readme(items) -> str:
    ordered = sorted(items, key=lambda it: (it[1]["created"], it[1]["slug"]), reverse=True)
    cells = []
    for _folder, meta in ordered:
        slug = meta["slug"]
        thumb = _media(meta, "thumb")
        img = (f'<img src="models/{slug}/{thumb}" width="240" alt="{meta["title"]["en"]}">'
               if thumb else "")
        cells.append(
            f'<a href="models/{slug}/">{img}</a><br><b><a href="models/{slug}/">'
            f'{meta["title"]["en"]}</a></b><br><sub>{LICENSE_NAMES[meta["license"]][0]}</sub>')
    rows = []
    for i in range(0, len(cells), 3):
        chunk = cells[i:i + 3]
        rows.append("<tr>" + "".join(f'<td align="center" valign="top">{c}</td>' for c in chunk) + "</tr>")
    grid = "<table>\n" + "\n".join(rows) + "\n</table>" if rows else "_No models yet._"

    return "\n".join([
        "<!-- Generated by tools/gallery.py. Do not edit: change meta.json or the generator. -->",
        "# ArgilCAD Gallery",
        "",
        f"Parametric 3D models made in [ArgilCAD]({SITE_URL}) — every one is a "
        "[build123d](https://github.com/gumyr/build123d) Python script you can open, "
        "change and print.",
        "",
        f"**{len(items)} models.** Each folder holds the script (`model.py`, the source of "
        "truth), its description (`meta.json`), a 3D preview (`model.glb`), four fixed views, "
        "a thumbnail and a turntable. [`index.jsonl`](index.jsonl) lists them all, one line "
        "each.",
        "",
        grid,
        "",
        "## Use a model",
        "",
        f"1. Open [ArgilCAD]({APP_URL}) in a browser (or the desktop app).",
        "2. Paste the model's `model.py` into the code editor and run it.",
        "3. Change any number, or ask the AI for a change. Print it, export it.",
        "",
        "Outside the app every model is a plain build123d script: "
        "`pip install -r tools/requirements.txt`, then `python tools/runtime.py "
        "models/<slug>/model.py` builds it and prints what it measured.",
        "",
        "## Licences",
        "",
        "Every model carries its own licence in `meta.json` — by default "
        f"{_license_link('CC-BY-NC-SA-4.0')}: share and remix with credit, not commercially, "
        "and remixes under the same terms. See [LICENSE.md](LICENSE.md). "
        "**AI training on this gallery is welcome**; the licence still applies to copies of "
        "the models themselves. The tooling is MIT.",
        "",
        "## Adding a model",
        "",
        "Models come in through ArgilCAD itself (\"Share to gallery\", coming soon) and are "
        "reviewed before they appear here; pull requests from outside are closed. See "
        "[CONTRIBUTING.md](CONTRIBUTING.md).",
        "",
        "---",
        "",
        "## Türkçe",
        "",
        f"[ArgilCAD]({SITE_URL}) ile yapılmış parametrik 3B modeller. Her biri açıp "
        "değiştirebileceğin ve basabileceğin bir build123d Python betiği. Bir modelin "
        f"`model.py` dosyasını [ArgilCAD]({APP_URL}) kod düzenleyicisine yapıştırıp "
        "çalıştırman yeterli. Lisanslar model başına `meta.json` içinde; varsayılan "
        "CC BY-NC-SA 4.0 (atıfla paylaş ve değiştir, ticari kullanım yok). Yapay zekâ "
        "eğitimine açıktır.",
        "",
    ])


def reuse_toml(items) -> str:
    lines = [
        "# Generated by tools/gallery.py. Do not edit.",
        "# Machine-readable licensing (https://reuse.software): the tooling and texts",
        "# are MIT; each model folder carries the licence its meta.json names.",
        "version = 1",
        "",
        "[[annotations]]",
        'path = ["tools/**", ".github/**", "schema/**", "docs/**", "*.md", "index.jsonl", '
        '"withdrawn.jsonl", "REUSE.toml", ".gitignore"]',
        'precedence = "aggregate"',
        f'SPDX-FileCopyrightText = "{OWNER_COPYRIGHT}"',
        'SPDX-License-Identifier = "MIT"',
        "",
    ]
    for _folder, meta in sorted(items, key=lambda it: it[1]["slug"]):
        lines += [
            "[[annotations]]",
            f'path = "models/{meta["slug"]}/**"',
            'precedence = "override"',
            f'SPDX-FileCopyrightText = "{meta["copyright"]}"',
            f'SPDX-License-Identifier = "{meta["license"]}"',
            "",
        ]
    return "\n".join(lines)


def generated_files(items) -> Dict[Path, str]:
    out = {
        INDEX: "\n".join(index_lines(items)) + ("\n" if items else ""),
        README: root_readme(items),
        REUSE: reuse_toml(items),
    }
    for folder, meta in items:
        out[folder / "README.md"] = model_readme(meta)
    # REUSE refuses a licence text no file uses, so LICENSES/ holds only the
    # licences in use; the texts of all the offered ones wait in tools/licenses.
    for spdx in sorted({meta["license"] for _f, meta in items}):
        out[LICENSES / f"{spdx}.txt"] = (LICENSE_STORE / f"{spdx}.txt").read_text(encoding="utf-8")
    return out


def stale_licenses(items) -> List[Path]:
    keep = set(generated_files(items)) | {LICENSES / "MIT.txt"}
    return [p for p in sorted(LICENSES.glob("*.txt")) if p not in keep]


def cmd_generate(_args) -> int:
    items = entries()
    for path, text in generated_files(items).items():
        if not path.exists() or path.read_text(encoding="utf-8") != text:
            path.write_text(text, encoding="utf-8")
            print(f"wrote {path.relative_to(ROOT)}")
    for path in stale_licenses(items):
        path.unlink()
        print(f"removed {path.relative_to(ROOT)} (no model uses it)")
    return 0


# ------------------------------------------------------------------ checking

class Problems:
    def __init__(self) -> None:
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def error(self, where: str, msg: str) -> None:
        self.errors.append(f"{where}: {msg}")

    def warn(self, where: str, msg: str) -> None:
        self.warnings.append(f"{where}: {msg}")


def _words(text: str) -> str:
    return " " + re.sub(r"[^\wçğıöşüâîû]+", " ", text.lower()) + " "


def check_content(slug: str, meta: Dict[str, Any], p: Problems) -> None:
    texts = [meta["title"]["en"], meta["title"]["tr"], meta["summary"]["en"],
             meta["summary"]["tr"], " ".join(meta["tags"])]
    if meta.get("prompt"):
        texts.append(meta["prompt"]["text"])
    blob = _words(" ".join(texts))
    for w in FORBIDDEN_WORDS:
        if f" {w} " in blob:
            p.error(slug, f"content policy: '{w}' (weapons are not accepted)")
    for w in BRAND_WORDS:
        if f" {w} " in blob:
            p.warn(slug, f"names '{w}': no brand or product names in the gallery")
    for pattern, what in PII_PATTERNS:
        for t in texts:
            if pattern.search(t):
                p.error(slug, f"looks like {what} in the text; remove personal data")


# A preview must open anywhere without a decoder or a second request:
# self-contained, uncompressed glTF 2.0.
COMPRESSED_GLTF = {"KHR_draco_mesh_compression", "EXT_meshopt_compression", "KHR_meshopt_compression",
                   "KHR_texture_basisu"}


def glb_problem(data: bytes) -> Optional[str]:
    import struct

    if len(data) < 20 or data[:4] != b"glTF" or struct.unpack_from("<I", data, 4)[0] != 2:
        return "is not a glTF 2.0 binary"
    n, kind = struct.unpack_from("<II", data, 12)
    if kind != 0x4E4F534A:
        return "has no JSON chunk"
    try:
        doc = json.loads(data[20:20 + n])
    except ValueError:
        return "has JSON that does not parse"
    if doc.get("extensionsRequired"):
        return f"requires {doc['extensionsRequired']}"
    if set(doc.get("extensionsUsed") or []) & COMPRESSED_GLTF:
        return "is compressed; publish it uncompressed"
    if any("uri" in b for b in (doc.get("buffers") or []) + (doc.get("images") or [])):
        return "points at files outside itself"
    return None


def check_media(folder: Path, meta: Dict[str, Any], p: Problems) -> None:
    from PIL import Image

    slug = meta["slug"]
    kinds = [m["kind"] for m in meta["media"]]
    for need in ("model", "thumb", "og"):
        if need not in kinds:
            p.error(slug, f"no {need} in media")
    if "turntable" not in kinds and "animation" not in kinds:
        p.error(slug, "no turntable or animation in media")
    views = {m.get("view") for m in meta["media"] if m["kind"] == "view"}
    for v in REQUIRED_VIEWS:
        if v not in views:
            p.error(slug, f"no {v} view in media")

    listed = set()
    for m in meta["media"]:
        f = folder / m["file"]
        listed.add(m["file"])
        if not f.exists():
            p.error(slug, f"{m['file']} is listed but missing")
            continue
        limit = MAX_BYTES[m["kind"]]
        if f.stat().st_size > limit:
            p.error(slug, f"{m['file']} is {f.stat().st_size // 1024} KB, over {limit // 1024} KB")
        if f.suffix in (".png", ".webp", ".jpg") and "size" in m:
            with Image.open(f) as img:
                if list(img.size) != m["size"]:
                    p.error(slug, f"{m['file']} is {img.size}, meta says {m['size']}")
    glb = folder / "model.glb"
    if glb.is_file():
        problem = glb_problem(glb.read_bytes())
        if problem:
            p.error(slug, f"model.glb {problem}")

    present = {str(x.relative_to(folder)) for x in folder.rglob("*") if x.is_file()}
    extra = present - listed - {"meta.json", "model.py", "README.md"}
    for e in sorted(extra):
        p.error(slug, f"{e} is not listed in meta.json")


def check_entry(folder: Path, meta: Dict[str, Any], all_meta: Dict[str, Dict[str, Any]],
                validator, p: Problems) -> None:
    slug = folder.name
    for err in sorted(validator.iter_errors(meta), key=lambda e: list(e.path)):
        where = "/".join(str(x) for x in err.path) or "(root)"
        p.error(slug, f"meta.json {where}: {err.message}")
    if p.errors and any(e.startswith(f"{slug}: meta.json") for e in p.errors):
        return
    if meta["slug"] != slug:
        p.error(slug, f"slug {meta['slug']!r} does not match the folder")

    code_path = folder / "model.py"
    if not code_path.exists():
        p.error(slug, "no model.py")
        return
    code = code_path.read_text(encoding="utf-8")
    if len(code.encode()) > MAX_CODE_BYTES:
        p.error(slug, "model.py is over 200 KB")
    # Code is English throughout — names, comments, labels — so it reads the
    # same to everyone. A Turkish letter anywhere is the reliable sign that a
    # translation is still owed; words spelled without them need a reviewer.
    for n, line in enumerate(code.splitlines(), 1):
        if NON_ENGLISH_LETTERS.search(line):
            p.error(slug, f"model.py line {n} is not in English: {line.strip()[:60]!r}")
            break
    try:
        if code_fingerprint(code) != meta["fingerprint"]["code_norm_sha256"]:
            p.error(slug, "model.py changed since it was published (fingerprint differs): re-publish it")
    except SyntaxError as exc:
        p.error(slug, f"model.py does not parse: {exc}")
    if geom_fingerprint(meta["metrics"]) != meta["fingerprint"]["geom"]:
        p.error(slug, "fingerprint.geom does not follow from the metrics")

    parent = meta.get("derived_from")
    if parent:
        src = all_meta.get(parent)
        if src is None:
            p.error(slug, f"derived_from {parent} is not in the gallery")
        else:
            if "SA" in src["license"] and meta["license"] != src["license"]:
                p.error(slug, f"remix of a ShareAlike model must keep {src['license']}")
            if "NC" in src["license"] and "NC" not in meta["license"]:
                p.error(slug, f"remix of a NonCommercial model must stay NonCommercial ({src['license']})")
    if meta["id"] in withdrawn_ids():
        p.error(slug, f"{meta['id']} was withdrawn and may not come back")

    check_content(slug, meta, p)
    check_media(folder, meta, p)


def build(folder: Path) -> Dict[str, Any]:
    try:
        out = subprocess.run(
            [sys.executable, str(RUNTIME), str(folder / "model.py")],
            capture_output=True, text=True, timeout=BUILD_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        return {"error": f"did not finish within {BUILD_TIMEOUT_S} s"}
    line = (out.stdout.strip().splitlines() or ["{}"])[-1]
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        return {"error": (out.stderr or out.stdout).strip()[-2000:] or "no output"}


def compare_metrics(slug: str, want: Dict[str, Any], got: Dict[str, Any], p: Problems) -> None:
    for key in ("face_count", "edge_count", "vertex_count"):
        if want.get(key) != got.get(key):
            p.error(slug, f"{key}: built {got.get(key)}, recorded {want.get(key)}")
    for key in ("volume", "area"):
        w, g = want.get(key), got.get(key)
        if g is None or abs(g - w) > max(METRIC_ABS_TOL, METRIC_REL_TOL * abs(w)):
            p.error(slug, f"{key}: built {g}, recorded {w}")
    for i, (w, g) in enumerate(zip(want["bbox"], got.get("bbox") or [None] * 3)):
        if g is None or abs(g - w) > METRIC_ABS_TOL:
            p.error(slug, f"bbox[{i}]: built {g}, recorded {w}")


def changed_slugs(ref: str) -> Optional[set]:
    out = subprocess.run(["git", "diff", "--name-only", ref, "--"], capture_output=True,
                         text=True, cwd=ROOT)
    if out.returncode != 0:
        return None
    files = out.stdout.split()
    if any(f.startswith(("tools/", "schema/")) for f in files):
        return None  # the tools changed: check everything
    return {f.split("/")[1] for f in files if f.startswith("models/") and f.count("/") >= 2}


def cmd_check(args) -> int:
    import jsonschema

    validator = jsonschema.Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8")))
    items = entries()
    p = Problems()

    ids: Dict[str, str] = {}
    for folder, meta in items:
        if meta.get("id") in ids:
            p.error(folder.name, f"id {meta['id']} is also {ids[meta['id']]}")
        ids[meta.get("id")] = folder.name
    all_meta = {meta.get("id"): meta for _f, meta in items}
    for folder in sorted(MODELS.iterdir()) if MODELS.exists() else []:
        if folder.is_dir() and not (folder / "meta.json").exists():
            p.error(folder.name, "folder has no meta.json")

    selected = items
    if args.only:
        selected = [it for it in items if it[0].name in args.only]
        if not selected:
            p.error("check", f"no entry named {args.only}")
    elif args.changed:
        slugs = changed_slugs(args.changed)
        if slugs is not None:
            selected = [it for it in items if it[0].name in slugs]

    for folder, meta in selected:
        check_entry(folder, meta, all_meta, validator, p)

    # The derived files must be what the generator makes of the entries.
    for path, text in generated_files(items).items():
        if not path.exists() or path.read_text(encoding="utf-8") != text:
            p.error(str(path.relative_to(ROOT)), "out of date: run `python tools/gallery.py generate`")
    for path in stale_licenses(items):
        p.error(str(path.relative_to(ROOT)), "no model uses it: run `python tools/gallery.py generate`")

    if not args.no_build:
        for folder, meta in selected:
            if any(e.startswith(f"{folder.name}:") for e in p.errors):
                continue
            print(f"building {folder.name} …", flush=True)
            got = build(folder)
            if "error" in got:
                p.error(folder.name, f"does not build: {got['error']}")
                continue
            compare_metrics(folder.name, meta["metrics"], got["metrics"], p)

    for w in p.warnings:
        print(f"warning: {w}")
    for e in p.errors:
        print(f"error: {e}")
    print(f"{len(selected)} entr{'y' if len(selected) == 1 else 'ies'} checked, "
          f"{len(p.errors)} error(s), {len(p.warnings)} warning(s)")
    return 1 if p.errors else 0


def cmd_reverify(_args) -> int:
    """Build everything with the installed engine and report drift. Writes
    nothing: media stay as published, and a drift is for a person to read."""
    p = Problems()
    rows = []
    for folder, meta in entries():
        got = build(folder)
        if "error" in got:
            p.error(folder.name, got["error"])
            rows.append(f"| {folder.name} | ✗ | {got['error'][:80]} |")
            continue
        before = len(p.errors)
        compare_metrics(folder.name, meta["metrics"], got["metrics"], p)
        rows.append(f"| {folder.name} | {'✓' if len(p.errors) == before else '✗'} | "
                    f"{got['build_ms']} ms |")
    report = "\n".join(["| model | holds | |", "|---|---|---|"] + rows)
    print(report)
    for e in p.errors:
        print(f"error: {e}")
    return 1 if p.errors else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("generate")
    c = sub.add_parser("check")
    c.add_argument("--only", nargs="+")
    c.add_argument("--changed", metavar="GIT_REF", help="only entries changed since this ref")
    c.add_argument("--no-build", action="store_true")
    sub.add_parser("reverify")
    args = ap.parse_args(argv)
    return {"generate": cmd_generate, "check": cmd_check, "reverify": cmd_reverify}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
