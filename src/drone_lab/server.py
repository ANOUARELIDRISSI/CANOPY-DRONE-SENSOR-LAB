"""Local 3D view and server-sent telemetry. Start with `uv run drone-live`."""

import argparse
import asyncio
import json
import os
import secrets
import threading
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import joblib
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from drone_lab.environment import Environment
from drone_lab.simulation import LINKS
from drone_lab.streaming import StreamSession


class StartRequest(BaseModel):
    scenario: str = "fire"
    runs: int = Field(default=1, ge=1, le=300)
    steps: int = Field(default=120, ge=30, le=600)
    seed: int = Field(default_factory=lambda: secrets.randbits(32), ge=0, le=2**32 - 1)
    speed: float = Field(default=4, ge=0.25, le=64)
    drones: int = Field(default=1, ge=1, le=8)
    environment: str = "forest"
    field_width: float = Field(default=220, ge=150, le=600)
    sensors: int = Field(default=12, ge=6, le=60)
    vegetation: int = Field(default=70, ge=0, le=100)


class Runtime:
    def __init__(self, model: dict, output_root: Path):
        self.model, self.output_root = model, output_root
        self.lock = threading.RLock()
        self.session: StreamSession | None = None
        self.worker: threading.Thread | None = None
        self.stop_event = threading.Event()
        self.error: str | None = None
        self.speed = 1.0

    def start(self, options: StartRequest) -> str:
        with self.lock:
            if self.worker is not None and self.worker.is_alive():
                raise ValueError("A collection is already running; stop it before starting another")
            if options.scenario not in ("normal", "fire", "nuisance", "mixed"):
                raise ValueError("Choose normal, fire, nuisance or mixed")
            session_name = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8]
            self.session = StreamSession(
                self.output_root / session_name,
                self.model,
                options.seed,
                options.runs,
                options.steps,
                options.scenario,
                options.drones,
                Environment(
                    options.environment, options.field_width, options.sensors, options.vegetation
                ),
            )
            self.stop_event.clear()
            self.speed = options.speed
            self.error = None
            self.worker = threading.Thread(target=self._run, args=(options.speed,), daemon=True)
            self.worker.start()
            return session_name

    def _run(self, speed: float) -> None:
        start = time.monotonic()
        try:
            while not self.stop_event.is_set():
                with self.lock:
                    assert self.session is not None
                    self.session.advance((time.monotonic() - start) * speed)
                    if self.session.status != "running":
                        break
                self.stop_event.wait(0.05)
        except Exception as exc:
            with self.lock:
                self.error = f"Collection failed: {type(exc).__name__}: {exc}"
                if self.session:
                    self.session.close("failed")
        finally:
            with self.lock:
                if self.session:
                    self.session.close()

    def stop(self) -> None:
        self.stop_event.set()
        if self.worker:
            self.worker.join(timeout=10)

    def snapshot(self) -> dict:
        with self.lock:
            if self.session:
                return self.session.snapshot() | {"error": self.error, "speed": self.speed}
            return preview_state(StartRequest()) | {"status": "idle"}


def preview_state(options: StartRequest) -> dict:
    environment = Environment(
        options.environment, options.field_width, options.sensors, options.vegetation
    )
    paths = environment.paths(options.steps, options.drones)
    return {
        "status": "preview",
        "session": None,
        "seed": options.seed,
        "steps": options.steps,
        "environment": environment.to_dict(),
        "drone_count": options.drones,
        "route": paths[0].tolist(),
        "runs": options.runs,
        "run_id": 0,
        "time_s": 0,
        "elapsed_s": 0,
        "total_s": options.runs * options.steps * 2,
        "speed": options.speed,
        "scenario_mode": options.scenario,
        "scenario": options.scenario,
        "drones": [
            {
                "id": i,
                "position": path[0].tolist(),
                "heading": 0,
                "altitude_m": 14 + i * 2,
                "collected": 0,
            }
            for i, path in enumerate(paths)
        ],
        "stations": [
            {
                "id": i,
                "x": float(point[0]),
                "y": float(point[1]),
                "protocol": list(LINKS)[i % 3],
                "decision": "WARNING",
                "age_s": None,
                "in_range": False,
                "reading": None,
            }
            for i, point in enumerate(environment.positions())
        ],
        "counts": {"received": 0, "lost": 0, "out_of_range": 0, "duplicates": 0},
        "links": {name: {"received": 0, "lost": 0, "out_of_range": 0} for name in LINKS},
    }


def create_app(runtime: Runtime) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app):
        yield
        runtime.stop()

    app = FastAPI(title="Drone Sensor Lab Live", lifespan=lifespan)

    @app.get("/api/state")
    def state():
        return runtime.snapshot() | {"camera_port": int(os.getenv("CAMERA_PORT", "8766"))}

    @app.post("/api/start")
    def start(options: StartRequest):
        try:
            return {"session": runtime.start(options)}
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/api/stop")
    def stop():
        runtime.stop()
        return runtime.snapshot()

    @app.post("/api/preview")
    def preview(options: StartRequest):
        try:
            return preview_state(options)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.get("/api/events")
    async def events():
        async def frames():
            while True:
                yield (
                    "data: "
                    + json.dumps(
                        runtime.snapshot() | {"camera_port": int(os.getenv("CAMERA_PORT", "8766"))},
                        allow_nan=False,
                    )
                    + "\n\n"
                )
                await asyncio.sleep(0.2)

        return StreamingResponse(
            frames(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.get("/api/download/{filename}")
    def download(filename: str):
        if filename not in ("readings.csv", "raw.jsonl", "manifest.json"):
            raise HTTPException(404, "Unknown artifact")
        with runtime.lock:
            if runtime.session is None:
                raise HTTPException(404, "Start a collection first")
            if filename == "manifest.json":
                runtime.session.write_manifest()
            content = (runtime.session.output / filename).read_bytes()
        return Response(
            content,
            media_type="text/csv" if filename.endswith("csv") else "application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    app.mount("/", StaticFiles(directory=Path(__file__).parent / "web", html=True), name="viewer")
    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="Live 3D drone collection and CSV streaming")
    parser.add_argument("--model", type=Path, default=Path("artifacts/demo/model.joblib"))
    parser.add_argument("--output-root", type=Path, default=Path("artifacts/live"))
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()
    if not args.model.is_file():
        parser.error("Model not found. Run uv run drone-lab first or provide --model.")
    runtime = Runtime(joblib.load(args.model), args.output_root)
    uvicorn.run(create_app(runtime), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
