#!/usr/bin/env python3
"""PR-G data builder — generate landmark & housing-complex seeds from OSM.

Run with plain CPython (stdlib only) + network to overpass-api.de:

    python3 backend/scripts/seed_locations_from_osm.py

Strategy: country-wide Overpass queries time out (504), so we query
region-by-region using a bounding box computed from that region's
microdistrict pins (`frontend/src/shared/constants/microdistricts.ts`).
Each OSM POI / apartment building is then pinned to a district (and maybe
a microdistrict) by the NEAREST pin within that region — and the pin's
`district` is already a REGIONS key, so no OSM-name ↔ key matching is
needed. Region is derived from district via DISTRICT_TO_REGION.

Outputs (one JSON object per line for clean diffs):
    backend/app/data/landmarks_seed.json
    backend/app/data/housing_complexes_seed.json

Overpass enforces a 2-slot-per-IP rate limit; we wait for a free slot,
retry on rate-limit / 504, and skip (not abort) a region that keeps
failing so partial coverage still lands.
"""

from __future__ import annotations

import importlib.util
import json
import math
import os
import re
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BACKEND = REPO / "backend"
MICRO_TS = REPO / "frontend/src/shared/constants/microdistricts.ts"
OUT_DIR = BACKEND / "app" / "data"
OVERPASS = "https://overpass-api.de/api/interpreter"
STATUS_URL = "https://overpass-api.de/api/status"
UA = "ucharmarket-seed/1.0 (b.gaybullaev@gmail.com)"

DISTRICT_MAX_KM = 7.0
MICRO_MAX_KM = 1.6
BBOX_PAD_DEG = 0.06  # ~6.5 km padding around a region's microdistrict hull

# ─────────────────────────── reference data ────────────────────────────


def load_d2r():
    spec = importlib.util.spec_from_file_location(
        "regions_mod", BACKEND / "app" / "core" / "regions.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod.DISTRICT_TO_REGION


def load_microdistricts():
    text = MICRO_TS.read_text(encoding="utf-8")
    out = []
    obj_re = re.compile(
        r'\{[^{}]*?district:\s*"([^"]+)"[^{}]*?lat:\s*([-\d.]+)'
        r"[^{}]*?lng:\s*([-\d.]+)[^{}]*?\}"
    )
    name_re = re.compile(r'name:\s*"([^"]*)"')
    for m in obj_re.finditer(text):
        nm = name_re.search(m.group(0))
        out.append(
            (nm.group(1) if nm else "", m.group(1), float(m.group(2)), float(m.group(3)))
        )
    return out


# ───────────────────────── transliteration ─────────────────────────────

_LATN_DIGRAPHS = [
    ("o‘", "ў"), ("o'", "ў"), ("oʻ", "ў"), ("g‘", "ғ"), ("g'", "ғ"), ("gʻ", "ғ"),
    ("sh", "ш"), ("ch", "ч"), ("yo", "ё"), ("yu", "ю"), ("ya", "я"), ("ts", "ц"),
]
_LATN_SINGLES = {
    "a": "а", "b": "б", "d": "д", "e": "е", "f": "ф", "g": "г", "h": "ҳ",
    "i": "и", "j": "ж", "k": "к", "l": "л", "m": "м", "n": "н", "o": "о",
    "p": "п", "q": "қ", "r": "р", "s": "с", "t": "т", "u": "у", "v": "в",
    "x": "х", "y": "й", "z": "з", "c": "с", "w": "в",
}
_RU_TO_LATN = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo",
    "ж": "j", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "x", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sh", "ъ": "",
    "ы": "i", "ь": "", "э": "e", "ю": "yu", "я": "ya", "ў": "o‘", "ғ": "g‘",
    "қ": "q", "ҳ": "h", "ҷ": "j",
}


def _has_cyrillic(s):
    return any("а" <= c.lower() <= "я" or c in "ўғқҳё" for c in s)


def _is_latin(s):
    return any("a" <= c.lower() <= "z" for c in s) and not _has_cyrillic(s)


def latn_to_cyrl(s):
    if not s or not _is_latin(s):
        return s
    res = s
    for a, b in _LATN_DIGRAPHS:
        res = res.replace(a, b).replace(a.capitalize(), b.upper())
    out = []
    for ch in res:
        low = ch.lower()
        if low in _LATN_SINGLES:
            rep = _LATN_SINGLES[low]
            out.append(rep.upper() if ch.isupper() else rep)
        else:
            out.append(ch)
    return "".join(out)


def ru_to_latn(s):
    if not s or not _has_cyrillic(s):
        return s
    out = []
    for ch in s:
        low = ch.lower()
        if low in _RU_TO_LATN:
            rep = _RU_TO_LATN[low]
            out.append(rep.capitalize() if ch.isupper() and rep else rep)
        else:
            out.append(ch)
    return "".join(out)


def derive_names(tags):
    base = tags.get("name", "").strip()
    name = (tags.get("name:ru") or base).strip()
    uz_latn = (tags.get("name:uz") or tags.get("name:uz-Latn") or "").strip()
    uz_cyrl = (tags.get("name:uz-Cyrl") or "").strip()
    if not uz_latn:
        uz_latn = base if _is_latin(base) else ru_to_latn(name)
    if not uz_cyrl:
        uz_cyrl = latn_to_cyrl(uz_latn) if _is_latin(uz_latn) else uz_latn
    return name or base, uz_latn or name, uz_cyrl or name


# ─────────────────────────── geo helpers ───────────────────────────────


def haversine(lat1, lng1, lat2, lng2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def coords(el):
    if el.get("type") == "node":
        return el.get("lat"), el.get("lon")
    c = el.get("center")
    return (c["lat"], c["lon"]) if c else (None, None)


def assign(lat, lng, micros, d2r):
    best, best_km = None, 1e9
    for nm, dist, mlat, mlng in micros:
        km = haversine(lat, lng, mlat, mlng)
        if km < best_km:
            best_km, best = km, (nm, dist)
    if best is None or best_km > DISTRICT_MAX_KM:
        return None, None, None
    micro = best[0] if best_km <= MICRO_MAX_KM and best[0] else None
    return d2r.get(best[1]), best[1], micro


# ─────────────────────────── overpass I/O ──────────────────────────────


def _get(url, data=None, timeout=60):
    req = urllib.request.Request(
        url, data=data, headers={"User-Agent": UA, "Accept": "*/*"}
    )
    return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8")


def wait_for_slot():
    for _ in range(40):
        try:
            s = _get(STATUS_URL, timeout=30)
        except Exception:
            time.sleep(6)
            continue
        m = re.search(r"(\d+) slots available now", s)
        if m and int(m.group(1)) > 0:
            return
        w = re.search(r"in (\d+) seconds", s)
        time.sleep((int(w.group(1)) + 2) if w else 10)


def overpass(query, label=""):
    for attempt in range(6):
        wait_for_slot()
        try:
            raw = _get(
                OVERPASS,
                data=urllib.parse.urlencode({"data": query}).encode(),
                timeout=180,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"   ! {label} transport ({exc}); retry {attempt + 1}/6", flush=True)
            time.sleep(min(60, 10 * (attempt + 1)))
            continue
        if "rate_limited" in raw:
            print(f"   ! {label} rate-limited; waiting {attempt + 1}/6", flush=True)
            time.sleep(min(90, 15 * (attempt + 1)))
            continue
        if "runtime error" in raw:
            print(f"   ! {label} runtime error; retry {attempt + 1}/6", flush=True)
            time.sleep(min(60, 12 * (attempt + 1)))
            continue
        return json.loads(raw)
    raise RuntimeError(f"overpass failed: {label}")


def region_query(s, w, n, e):
    bb = f"({s:.4f},{w:.4f},{n:.4f},{e:.4f})"
    tags = [
        '["amenity"="marketplace"]', '["shop"="mall"]', '["amenity"="university"]',
        '["amenity"="college"]', '["leisure"="park"]', '["amenity"="hospital"]',
        '["railway"="station"]', '["amenity"="bus_station"]', '["leisure"="stadium"]',
        '["aeroway"="aerodrome"]', '["tourism"="museum"]', '["amenity"="theatre"]',
        '["building"="apartments"]', '["residential"="apartments"]',
    ]
    body = "\n".join(f'  nwr{t}["name"]{bb};' for t in tags)
    return f"[out:json][timeout:120];\n(\n{body}\n);\nout center tags;"


# ──────────────────────────── classify ─────────────────────────────────


def is_apartment(tags):
    return tags.get("building") == "apartments" or tags.get("residential") == "apartments"


def classify(tags):
    if tags.get("amenity") == "marketplace":
        return "market"
    if tags.get("shop") == "mall":
        return "mall"
    if tags.get("amenity") in ("university", "college"):
        return "university"
    if tags.get("leisure") == "park":
        return "park"
    if tags.get("amenity") == "hospital":
        return "hospital"
    if tags.get("railway") == "station" or tags.get("amenity") == "bus_station":
        return "station"
    if tags.get("leisure") == "stadium":
        return "stadium"
    if tags.get("aeroway") == "aerodrome":
        return "airport"
    if tags.get("tourism") == "museum":
        return "museum"
    if tags.get("amenity") == "theatre":
        return "theatre"
    return "other"


_HC_STOP = {"дом", "корпус", "блок", "подъезд", "новостройка", "house", "block"}
# OSM tags many non-residential buildings as building=apartments; drop names
# that are clearly an organization / civic object / bare house number.
_HC_BAD_SUBSTR = (
    "институт", "instituti", "филиал", "filial", "банк", "detsad", "детсад",
    "мастерская", "masterskaya", "школа", "maktab", "мактаб", "склад", "ombor",
    "магазин", "do'kon", "кафедра", "клиник", "klinik", "поликлин", "завод",
    "fabrika", "фабрика", "ателье", "колледж", "kollej", "лицей", "litsey",
    "гимназия", "gimnaziya", "group", "группа", " цех", "цех ", "офис", "office",
    "markaz", "марказ", "поликлиника", "больниц", "shifoxona", "аптек", "apteka",
    "церков", "мечеть", "masjid", "масжид", "храм", "music", "museum", "музей",
)
_HC_NUM_HOUSE = re.compile(r"^\d+[\s\-]?(uy|уй|уя|dom|дом|maxalla|mahalla|kvartal|кв)\b")


def clean_hc_name(name):
    n = name.strip()
    if len(n) < 3 or re.fullmatch(r"[\d\W_]+", n) or n.lower() in _HC_STOP:
        return None
    low = n.lower()
    if _HC_NUM_HOUSE.match(low):  # "23-uy", "46-mahalla", "12 dom"
        return None
    if any(b in low for b in _HC_BAD_SUBSTR):
        return None
    return n


def make_row(el, tags, micros, d2r):
    lat, lng = coords(el)
    if lat is None or lng is None:
        return None
    region, district, micro = assign(lat, lng, micros, d2r)
    if not district:
        return None
    name, nl, nc = derive_names(tags)
    return {
        "name": name,
        "name_uz_latn": nl,
        "name_uz_cyrl": nc,
        "region": region,
        "district": district,
        "microdistrict": micro,
        "latitude": round(lat, 6),
        "longitude": round(lng, 6),
        "osm_id": f"{el.get('type')}/{el.get('id')}",
        "source": "osm",
    }


# ───────────────────────────── driver ──────────────────────────────────


def compute_bboxes(micros, d2r):
    grp = defaultdict(list)
    for _nm, dist, lat, lng in micros:
        reg = d2r.get(dist)
        if reg:
            grp[reg].append((lat, lng))
    out = {}
    for reg, pts in grp.items():
        lats = [p[0] for p in pts]
        lngs = [p[1] for p in pts]
        out[reg] = (
            min(lats) - BBOX_PAD_DEG, min(lngs) - BBOX_PAD_DEG,
            max(lats) + BBOX_PAD_DEG, max(lngs) + BBOX_PAD_DEG,
        )
    return out


def split_bbox(b, nx, ny):
    """Split a (s, w, n, e) bbox into nx*ny tiles — lighter Overpass queries
    that dodge the 504/runtime errors big regions trigger."""
    s, w, n, e = b
    out = []
    for i in range(ny):
        for j in range(nx):
            out.append(
                (
                    s + (n - s) * i / ny, w + (e - w) * j / nx,
                    s + (n - s) * (i + 1) / ny, w + (e - w) * (j + 1) / nx,
                )
            )
    return out


def stats(label, rows):
    regs = Counter(r["region"] for r in rows)
    print(f"  {label}: {len(rows)} rows across {len(regs)} regions")
    if rows and "category" in rows[0]:
        print("    categories:", dict(Counter(r["category"] for r in rows)))


def dump_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    body = ",\n".join(json.dumps(r, ensure_ascii=False) for r in rows)
    path.write_text(f"[\n{body}\n]\n", encoding="utf-8")


def fetch_elements(reg, bbox):
    """Fetch a region; on failure split the bbox 2x2 and union the tiles."""
    try:
        return overpass(region_query(*bbox), label=reg).get("elements", [])
    except RuntimeError:
        print(f"   ! {reg} whole-bbox failed; splitting 2x2", flush=True)
        els, ok = [], False
        for i, sb in enumerate(split_bbox(bbox, 2, 2)):
            try:
                els += overpass(region_query(*sb), label=f"{reg}#{i}").get("elements", [])
                ok = True
            except RuntimeError:
                print(f"   ! {reg}#{i} sub-bbox failed", flush=True)
        if not ok:
            raise RuntimeError(f"{reg} all sub-bboxes failed")
        return els


def absorb(els, reg_micros, d2r, lm, hc):
    a_lm = a_hc = 0
    for el in els:
        tags = el.get("tags", {})
        if not tags.get("name", "").strip():
            continue
        row = make_row(el, tags, reg_micros, d2r)
        if not row:
            continue
        oid = row["osm_id"]
        if oid in lm or oid in hc:
            continue
        if is_apartment(tags):
            cleaned = clean_hc_name(row["name"])
            if not cleaned:
                continue
            row["name"] = cleaned
            hc[oid] = row
            a_hc += 1
        else:
            row["category"] = classify(tags)
            lm[oid] = row
            a_lm += 1
    return a_lm, a_hc


def main():
    only = set(filter(None, os.environ.get("ONLY_REGIONS", "").split(",")))
    append = os.environ.get("APPEND") == "1"
    d2r = load_d2r()
    micros = load_microdistricts()
    bboxes = compute_bboxes(micros, d2r)
    print(
        f"Loaded {len(micros)} pins, {len(d2r)} keys, {len(bboxes)} regions"
        + (f"; ONLY={sorted(only)}" if only else "")
        + ("; APPEND" if append else ""),
        flush=True,
    )

    lm, hc = {}, {}  # osm_id → row (dedup across overlapping bboxes)
    if append:
        # Reload prior seeds, re-running the (now stricter) HC filter to prune noise.
        for fn, store, is_hc in [
            ("landmarks_seed.json", lm, False),
            ("housing_complexes_seed.json", hc, True),
        ]:
            p = OUT_DIR / fn
            if not p.exists():
                continue
            kept = dropped = 0
            for r in json.loads(p.read_text(encoding="utf-8")):
                if is_hc and not clean_hc_name(r["name"]):
                    dropped += 1
                    continue
                store[r["osm_id"]] = r
                kept += 1
            print(f"  reloaded {fn}: kept {kept}, dropped {dropped}", flush=True)

    for reg, bbox in sorted(bboxes.items()):
        if only and reg not in only:
            continue
        reg_micros = [m for m in micros if d2r.get(m[1]) == reg]
        print(f"Region {reg}: {len(reg_micros)} pins, bbox {tuple(round(x,2) for x in bbox)}", flush=True)
        try:
            els = fetch_elements(reg, bbox)
        except RuntimeError as exc:
            print(f"   ! SKIP {reg}: {exc}", flush=True)
            continue
        a_lm, a_hc = absorb(els, reg_micros, d2r, lm, hc)
        print(f"   fetched {len(els)} elems → +{a_lm} landmarks, +{a_hc} HC", flush=True)
        time.sleep(3)

    landmarks = sorted(lm.values(), key=lambda r: (r["region"], r["district"], r["name"]))
    housing = sorted(hc.values(), key=lambda r: (r["region"], r["district"], r["name"]))
    stats("landmarks", landmarks)
    stats("housing_complexes", housing)
    dump_jsonl(OUT_DIR / "landmarks_seed.json", landmarks)
    dump_jsonl(OUT_DIR / "housing_complexes_seed.json", housing)
    print(f"Wrote seeds to {OUT_DIR}", flush=True)


if __name__ == "__main__":
    main()
