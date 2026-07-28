"""Standalone Pattern Generator demo — local Flask UI."""

from __future__ import annotations

import urllib.request
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory

from engine import build_recoil_steps, detect_points_and_preview

ROOT = Path(__file__).resolve().parent
SAMPLES = ROOT / "samples"

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024  # 32 MB


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/samples/<path:name>")
def sample_file(name: str):
    return send_from_directory(SAMPLES, name)


@app.get("/api/health")
def health():
    return jsonify(ok=True, app="PatternGenerator-Demo")


@app.post("/api/detect")
def detect():
    try:
        detect_style = (request.form.get("detect_style") or "generic").strip()
        file = request.files.get("spray_file")
        if not file or not file.filename:
            return jsonify(ok=False, error="Select an image or GIF first."), 400
        raw = file.read()
        if not raw:
            return jsonify(ok=False, error="Empty file."), 400
        data = detect_points_and_preview(raw, detect_style=detect_style)
        return jsonify(data)
    except Exception as exc:  # noqa: BLE001 — demo surface
        return jsonify(ok=False, error=str(exc)), 400


@app.post("/api/detect-url")
def detect_url():
    try:
        body = request.get_json(force=True, silent=True) or {}
        media_url = (body.get("media_url") or "").strip()
        detect_style = (body.get("detect_style") or "generic").strip()
        if not media_url:
            return jsonify(ok=False, error="Paste an image/GIF URL first."), 400
        with urllib.request.urlopen(media_url, timeout=30) as resp:  # noqa: S310 — local demo tool
            raw = resp.read()
        data = detect_points_and_preview(raw, detect_style=detect_style)
        return jsonify(data)
    except Exception as exc:  # noqa: BLE001
        return jsonify(ok=False, error=str(exc)), 400


@app.post("/api/preview")
def preview():
    try:
        body = request.get_json(force=True, silent=True) or {}
        points = body.get("points") or []
        data = build_recoil_steps(
            points,
            delay_ms=int(body.get("delay_ms") or 90),
            scale_x=float(body.get("scale_x") or 1.0),
            scale_y=float(body.get("scale_y") or 1.0),
            invert_x=bool(body.get("invert_x", True)),
            invert_y=bool(body.get("invert_y", True)),
        )
        return jsonify(data)
    except Exception as exc:  # noqa: BLE001
        return jsonify(ok=False, error=str(exc)), 400


def main() -> None:
    print("Pattern Generator Demo")
    print("Open http://127.0.0.1:5055")
    app.run(host="127.0.0.1", port=5055, debug=False)


if __name__ == "__main__":
    main()
