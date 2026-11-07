"""Optional local fire/smoke camera service with a pinned CPU ONNX model."""

import argparse
import asyncio
import hashlib
import io
import os
import time
import urllib.request
from pathlib import Path
from tempfile import NamedTemporaryFile

import numpy as np
import onnxruntime as ort
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from PIL import Image, ImageOps, UnidentifiedImageError

REVISION = "ca9af118478d34bcd8c55c46b3b5931be4175b69"
FILENAME = "yolov8n_fire_fp32_416.onnx"
URL = (
    f"https://raw.githubusercontent.com/prasodium/edge-fire-detection/{REVISION}/weights/{FILENAME}"
)
SHA256 = "0212d6037d879ad1750382101bc41131316c8cae1981031ed74c971e18f20952"
LABELS = ("small_flame", "smoke")
SIZE = 416


def weights(directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / FILENAME
    if path.exists():
        if hashlib.sha256(path.read_bytes()).hexdigest() != SHA256:
            raise ValueError(f"Cached camera weights failed SHA-256 verification: {path}")
        return path
    with urllib.request.urlopen(URL, timeout=90) as response:
        data = response.read(13_000_000)
    if hashlib.sha256(data).hexdigest() != SHA256:
        raise ValueError("Camera download failed SHA-256 verification")
    with NamedTemporaryFile(dir=directory, delete=False) as handle:
        handle.write(data)
        temp = Path(handle.name)
    os.replace(temp, path)
    return path


def detections(
    output: np.ndarray, size: tuple[int, int], scale: float, left: int, top: int
) -> list:
    """Convert YOLO center-format boxes to normalized source coordinates with per-class NMS."""
    rows = output[0].T
    ids = rows[:, 4:].argmax(axis=1)
    scores = rows[np.arange(len(rows)), 4 + ids]
    keep = np.flatnonzero(scores >= 0.45)
    keep = keep[np.argsort(scores[keep])[::-1]]
    boxes = np.column_stack(
        (
            rows[:, 0] - rows[:, 2] / 2,
            rows[:, 1] - rows[:, 3] / 2,
            rows[:, 0] + rows[:, 2] / 2,
            rows[:, 1] + rows[:, 3] / 2,
        )
    )
    areas = np.prod(np.maximum(0, boxes[:, 2:] - boxes[:, :2]), axis=1)
    found: list[dict] = []
    while len(keep) and len(found) < 20:
        i = keep[0]
        others = keep[1:]
        box = (boxes[i] - np.array([left, top, left, top])) / scale
        box = np.clip(box / np.array([*size, *size]), 0, 1)
        if box[2] > box[0] and box[3] > box[1]:
            found.append({"label": LABELS[ids[i]], "score": float(scores[i]), "box": box.tolist()})
        overlap = np.minimum(boxes[i, 2:], boxes[others, 2:]) - np.maximum(
            boxes[i, :2], boxes[others, :2]
        )
        intersection = np.prod(np.maximum(0, overlap), axis=1)
        iou = intersection / np.maximum(areas[i] + areas[others] - intersection, 1e-9)
        keep = others[(ids[i] != ids[others]) | (iou <= 0.45)]
    return found


class Detector:
    def __init__(self, path: Path):
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        options.inter_op_num_threads = 1
        options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        options.add_session_config_entry("session.intra_op.allow_spinning", "0")
        self.session = ort.InferenceSession(str(path), options, providers=["CPUExecutionProvider"])
        self.input = self.session.get_inputs()[0].name

    def infer(self, data: bytes) -> dict:
        start = time.perf_counter()
        with Image.open(io.BytesIO(data)) as source:
            if source.width * source.height > 8_000_000:
                raise ValueError("Frame exceeds 8 megapixels")
            img = ImageOps.exif_transpose(source).convert("RGB")
        scale = SIZE / max(img.size)
        resized = img.resize(
            (max(1, round(img.width * scale)), max(1, round(img.height * scale))),
            Image.Resampling.BILINEAR,
        )
        x, y = (SIZE - resized.width) // 2, (SIZE - resized.height) // 2
        padded = Image.new("RGB", (SIZE, SIZE), (114, 114, 114))
        padded.paste(resized, (x, y))
        tensor = np.ascontiguousarray(
            np.asarray(padded, dtype=np.float32).transpose(2, 0, 1)[None] / 255
        )
        raw = self.session.run(None, {self.input: tensor})[0]
        result = detections(raw, img.size, scale, x, y)
        return {
            "detections": result,
            "width": img.width,
            "height": img.height,
            "processing_ms": round((time.perf_counter() - start) * 1000, 1),
        }


def create_camera(detector: Detector) -> FastAPI:
    app = FastAPI(title="Drone Lab CPU Camera")
    gate = asyncio.Lock()
    web = Path(__file__).parent / "web"

    @app.get("/")
    def page():
        return FileResponse(web / "camera-view.html")

    @app.get("/camera-view.js")
    def script():
        return FileResponse(web / "camera-view.js", media_type="text/javascript")

    @app.get("/style.css")
    def style():
        return FileResponse(web / "style.css", media_type="text/css")

    @app.get("/reference.jpg")
    def reference():
        return FileResponse(web / "camera-reference.jpg", media_type="image/jpeg")

    @app.get("/health")
    def health():
        return {"model": FILENAME, "provider": detector.session.get_providers(), "threads": 2}

    @app.post("/infer")
    async def infer(request: Request):
        if gate.locked():
            raise HTTPException(429, "Camera busy; retry with the next frame")
        async with gate:
            frame = bytearray()
            async for chunk in request.stream():
                if len(frame) + len(chunk) > 2_000_000:
                    raise HTTPException(413, "Frame exceeds 2 MB")
                frame.extend(chunk)
            try:
                return await asyncio.to_thread(detector.infer, bytes(frame))
            except (
                ValueError,
                OSError,
                UnidentifiedImageError,
                Image.DecompressionBombError,
            ) as exc:
                raise HTTPException(422, "Invalid or oversized image") from exc

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--cache", type=Path, default=Path("artifacts/camera-models"))
    args = parser.parse_args()
    detector = Detector(weights(args.cache))
    uvicorn.run(create_camera(detector), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
