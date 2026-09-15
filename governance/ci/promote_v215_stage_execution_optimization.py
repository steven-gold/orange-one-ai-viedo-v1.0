#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import base64
import bz2

ROOT = Path(__file__).resolve().parents[2]
PAYLOAD = ROOT / "governance/ci/.v215_promotion_payload"
parts = sorted(PAYLOAD.glob("chunk_*.txt"))
if len(parts) != 6:
    raise SystemExit(f"BLOCK: expected 6 promotion payload chunks, found {len(parts)}")
encoded = "".join(p.read_text(encoding="utf-8").strip() for p in parts)
raw = bz2.decompress(base64.b64decode(encoded))
code = compile(raw.decode("utf-8"), __file__ + "::payload", "exec")
exec(code, {"__name__": "__main__", "__file__": __file__})
