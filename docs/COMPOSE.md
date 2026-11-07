# Compose workflow

From the repository root, start Linux containers with Docker Desktop:

```powershell
docker compose --profile camera up --build -d
docker compose --profile camera ps -a
```

Open [the viewer](http://127.0.0.1:8765), start a mission, then select **Camera view**. The camera panel can inspect the selected drone, a local image or video, or a webcam. Click **Test fire image** for the included example. The [standalone camera](http://127.0.0.1:8766) also accepts local media.

| Service | Purpose |
|---|---|
| `init` | Creates a first mixed batch and trains a sensor model when needed. Exit code 0 means initialization finished. |
| `viewer` | Runs the 3D simulation and streams normalized readings. |
| `batch` | Produces one new uniquely named collection per invocation. |
| `train` | Fits the selected classifier across completed datasets. |
| `camera` | Runs optional flame and smoke detection on CPU. |

Use `docker compose up --build -d` for the sensor services alone. `docker compose --profile camera down` stops this project. The host `artifacts/` folder persists. If the ports are occupied, set `$env:VIEWER_PORT` and `$env:CAMERA_PORT` to available ports before starting Compose.

## Collect and train

```powershell
docker compose run --rm batch --runs 30 --steps 120
docker compose run --rm batch --runs 30 --steps 120
docker compose run --rm train --classifier logistic_regression --include-live
docker compose restart viewer
```

Batches receive a random seed by default. Each new directory under `artifacts/batches/` contains its seed, manifest, raw packets, readings and per-tour summaries. Pass `--seed 42` to repeat a collection. Use a multiple of three runs, at least 15. The interactive viewer also chooses a fresh seed for each start. Uncheck **Random seed** to reproduce a mission.

Live sessions write their continuous `readings.csv` and a separate `batches/tour-XXXX.csv` for each tour with received readings. The trainer can include completed live sessions using the session-wide CSV. It skips repeated seed/tour pairs and splits by entire tours across batches. Choose `auto`, `random_forest` or `logistic_regression`. Each training job saves its metrics, source manifests, row counts and model under `artifacts/models/fit-*/`, then replaces `artifacts/models/current.joblib` atomically. Restart the viewer after a mission finishes to load that model.

## Camera model and example

The selected model is the 416-pixel FP32 YOLOv8n export for `small_flame` and `smoke`. Weights download on first camera startup to `artifacts/camera-models/`. The pinned SHA-256 is `0212d6037d879ad1750382101bc41131316c8cae1981031ed74c971e18f20952`. [Model source and benchmark](https://github.com/prasodium/edge-fire-detection/tree/ca9af118478d34bcd8c55c46b3b5931be4175b69)

ONNX Runtime uses two CPU threads. The browser waits for each response and allows a one-second interval between frames. Closing the view releases the camera. The selected-drone perspective hides station labels, alarm colors, routes and radio flashes. Fire or nuisance plumes are drawn from scenario state, and the detector receives only image pixels. Aerial footage and the illustrative 3D flames require their own accuracy evaluation. Vision output is displayed independently from sensor alarms.

The unmodified reference JPEG `flare_0014_jpg.rf.6ea81b6696f97d0d215876598a4c1ff8.jpg` is from LibreYOLO/fire-smoke-seg, distributed under CC BY 4.0. [Dataset](https://huggingface.co/datasets/LibreYOLO/fire-smoke-seg) · [License](https://creativecommons.org/licenses/by/4.0/)

## Native alternative

```powershell
uv sync --locked --all-groups --extra camera
uv run --extra camera python -m drone_lab.batches bootstrap
uv run --extra camera drone-live --model artifacts/models/current.joblib
# In a second terminal
uv run --extra camera python -m drone_lab.vision
```
