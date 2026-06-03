"""Publish step: write the data payload and copy the static dashboard into docs/.

The dashboard is a client-side app (web/index.html + app.js + styles.css) that
fetches data.json at load. Keeping the app in web/ (source-controlled) and the
generated output in docs/ (gitignored) means the build just copies + writes.
"""
import datetime
import json
import shutil
from pathlib import Path

WEB = Path("web")


def publish(out_dir: Path, payload: dict):
    out_dir.mkdir(exist_ok=True)
    payload = dict(payload)
    payload["generated"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    payload["date"] = datetime.date.today().isoformat()

    (out_dir / "data.json").write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")

    for name in ("index.html", "app.js", "styles.css"):
        src = WEB / name
        if src.exists():
            shutil.copyfile(src, out_dir / name)

    n = len(payload.get("stocks", []))
    print(f"wrote {out_dir/'data.json'} ({n} stocks) + copied web assets")
