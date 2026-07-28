"""Pattern Generator engine — image/GIF spray → (dx, dy, delay) steps."""

from __future__ import annotations

import base64
import io
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

try:
    from PIL import Image, ImageChops, ImageSequence
except Exception:  # pragma: no cover
    Image = None
    ImageChops = None
    ImageSequence = None


@dataclass
class SprayPoint:
    x: float
    y: float


def normalize_points(points: Sequence[dict]) -> List[SprayPoint]:
    normalized: List[SprayPoint] = []
    for point in points:
        try:
            x = float(point.get("x"))
            y = float(point.get("y"))
        except (TypeError, ValueError, AttributeError):
            continue
        normalized.append(SprayPoint(x=x, y=y))
    return normalized


def validate_points(points: Sequence[SprayPoint], minimum: int = 2) -> None:
    if len(points) < minimum:
        raise ValueError(f"At least {minimum} points are required.")


def _require_pillow() -> None:
    if Image is None:
        raise RuntimeError("Pillow is required. Run: pip install pillow")


def _to_data_url_png(img: "Image.Image") -> str:
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _collect_frames(image_bytes: bytes) -> List["Image.Image"]:
    _require_pillow()
    src = Image.open(io.BytesIO(image_bytes))
    if getattr(src, "is_animated", False):
        return [frame.convert("RGB") for frame in ImageSequence.Iterator(src)]
    return [src.convert("RGB")]


def _auto_suggest_points(frames: Sequence["Image.Image"], max_points: int = 96) -> List[Tuple[int, int]]:
    """Still-image heuristic: dark blobs, sorted top→bottom then left→right."""
    if not frames:
        return []
    width, height = frames[0].size
    darkness = [[255 for _ in range(width)] for _ in range(height)]

    for frame in frames:
        gray = frame.convert("L")
        pixels = gray.load()
        for y in range(height):
            row = darkness[y]
            for x in range(width):
                v = pixels[x, y]
                if v < row[x]:
                    row[x] = v

    flat = [v for row in darkness for v in row]
    flat.sort()
    threshold_idx = max(0, int(len(flat) * 0.04) - 1)
    threshold = min(150, flat[threshold_idx] if flat else 100)

    mask = [[darkness[y][x] <= threshold for x in range(width)] for y in range(height)]
    visited = [[False for _ in range(width)] for _ in range(height)]

    components: List[Tuple[float, float, int]] = []
    dirs = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    for y0 in range(height):
        for x0 in range(width):
            if visited[y0][x0] or not mask[y0][x0]:
                continue
            stack = [(x0, y0)]
            visited[y0][x0] = True
            sx = sy = count = 0
            while stack:
                x, y = stack.pop()
                sx += x
                sy += y
                count += 1
                for dx, dy in dirs:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < width and 0 <= ny < height and not visited[ny][nx] and mask[ny][nx]:
                        visited[ny][nx] = True
                        stack.append((nx, ny))
            if 3 <= count <= 600:
                components.append((sx / count, sy / count, count))

    components.sort(key=lambda c: (c[1], c[0]))
    return [(int(x), int(y)) for x, y, _ in components[:max_points]]


def _auto_suggest_gif_timeline(frames: Sequence["Image.Image"]) -> List[Tuple[int, int]]:
    """GIF timeline: frame-diff centroids ≈ chronological shot order."""
    if not frames or ImageChops is None:
        return []

    width, height = frames[0].size
    x0, y0 = int(width * 0.28), int(height * 0.18)
    x1, y1 = int(width * 0.72), int(height * 0.82)
    crop_w, crop_h = x1 - x0, y1 - y0
    if crop_w <= 0 or crop_h <= 0:
        return []

    points: List[Tuple[int, int]] = []
    prev = Image.new("L", (crop_w, crop_h), 0)
    threshold = 25
    min_pixels = 8

    for frame in frames:
        crop = frame.convert("L").crop((x0, y0, x1, y1))
        diff = ImageChops.difference(crop, prev)
        pixels = diff.load()
        coords = [
            (x, y)
            for y in range(crop_h)
            for x in range(crop_w)
            if pixels[x, y] > threshold
        ]
        if len(coords) >= min_pixels:
            sx = sum(c[0] for c in coords) / len(coords)
            sy = sum(c[1] for c in coords) / len(coords)
            points.append((int(sx + x0), int(sy + y0)))
        prev = crop

    return points


def detect_points_and_preview(image_bytes: bytes, detect_style: str = "generic") -> Dict[str, object]:
    frames = _collect_frames(image_bytes)
    style = (detect_style or "generic").strip().lower()

    if style in {"gif", "timeline", "cs2pulse"} and len(frames) > 1:
        points = _auto_suggest_gif_timeline(frames)
        recommended_frame = max(0, len(frames) - 1)
        style = "gif"
    else:
        points = _auto_suggest_points(frames)
        recommended_frame = 0
        style = "generic"

    preview = frames[recommended_frame].copy()
    frame_data_urls = [_to_data_url_png(frame) for frame in frames]
    return {
        "ok": True,
        "width": preview.width,
        "height": preview.height,
        "preview_data_url": _to_data_url_png(preview),
        "frame_data_urls": frame_data_urls,
        "frame_count": len(frame_data_urls),
        "recommended_frame_index": recommended_frame,
        "detect_style": style,
        "suggested_points": [{"x": x, "y": y} for x, y in points],
    }


def build_recoil_steps(
    raw_points: Sequence[dict],
    delay_ms: int = 90,
    scale_x: float = 1.0,
    scale_y: float = 1.0,
    invert_x: bool = True,
    invert_y: bool = True,
) -> Dict[str, object]:
    """Canonical export: consecutive point deltas → (dx, dy, delay)."""
    points = normalize_points(raw_points)
    validate_points(points)

    sign_x = -1.0 if invert_x else 1.0
    sign_y = -1.0 if invert_y else 1.0

    steps_ms: List[Tuple[float, float, int]] = []
    steps_seconds: List[Tuple[float, float, float]] = []
    lua_lines: List[str] = []

    for idx in range(1, len(points)):
        prev = points[idx - 1]
        curr = points[idx]
        dx = round((curr.x - prev.x) * scale_x * sign_x, 3)
        dy = round((curr.y - prev.y) * scale_y * sign_y, 3)
        steps_ms.append((dx, dy, int(delay_ms)))
        steps_seconds.append((dx, dy, round(delay_ms / 1000.0, 3)))
        lua_lines.append(
            f"MoveMouseRelativeFractional({dx} * kava * SensSetting, {dy} * kava * SensSetting)"
        )

    pattern_text = "\n".join(f"{x},{y},{d}" for x, y, d in steps_ms)
    lua_text = "\n".join(lua_lines)

    return {
        "ok": True,
        "pattern_text": pattern_text,
        "lua_text": lua_text,
        "steps_ms": [{"x": x, "y": y, "delay_ms": d} for x, y, d in steps_ms],
        "steps_count": len(steps_ms),
        "export_mode": "canonical",
    }
