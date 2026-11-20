"""Download a GGUF model into backend/models/. Run manually; no build does this."""
from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

DEST = Path(__file__).resolve().parents[1] / "models"


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: fetch_local_model.py <url> <filename.gguf>")
        return 2
    url, name = sys.argv[1], Path(sys.argv[2]).name
    if not name.endswith(".gguf"):
        name += ".gguf"
    DEST.mkdir(parents=True, exist_ok=True)
    target = DEST / name
    print(f"downloading {url} -> {target}")
    urllib.request.urlretrieve(url, target)
    print(f"done: {target.stat().st_size} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
