# Live 3D drone and streaming dataset

## Run

From the project root:

```powershell
uv sync --locked --all-groups
# Only if you do not already have a model:
uv run drone-lab --output artifacts/demo
uv run drone-live --model artifacts/demo/model.joblib --port 8765
```

Open http://127.0.0.1:8765. Select a scenario and click **Start collection**, then **Follow drone** for a close view of the Crazyflie model. Drag to orbit, scroll to zoom, or use **Overview**. Sensors have physical markers in the scene, and transmission lines flash when received samples update the viewer. There is no CDN dependency. The server listens on localhost only.

The live view uses an actual mesh from the cloned gym-pybullet-drones project. Movement follows the same path used in link-distance calculations, and the visual position comes from the server's simulation clock. This is a 3D kinematic visualization, not PyBullet dynamics: altitude is illustrative, the mesh is enlarged, and reception still uses 2D distance. See [asset provenance and licenses](THIRD_PARTY.md).

## How streaming works

1. A background worker advances simulation time from a monotonic wall clock multiplied by the chosen speed.
2. `SensorTour.sample()` generates readings as the drone reaches each two-second sample time. Both batch and live modes call this same implementation.
3. Range and loss determine received packets. Packets wait in an arrival-time priority queue; future arrivals cannot enter the CSV or visible readings.
4. Normalized rows are deduplicated, passed through the frozen model, written with Python's CSV writer and flushed after each update. Missing values are empty CSV cells and produce WARNING.
5. Server-sent events (`/api/events`) push a current-state snapshot about five times per second. The browser interpolates positions smoothly and updates station readings. SSE snapshots may skip intermediate visual updates; **the CSV retains every delivered unique reading**, including those between snapshots.

This is a live simulated producer, not replay of the previously generated CSV. It continues collecting when a browser disconnects. Reloading the page reconnects to the current session. Stop ends collection and closes files; stopping before all tours finish produces a partial dataset, labeled `stopped` in the manifest. Server shutdown stops its worker. There is no resume after process restart; start a new uniquely named session.

## CSV for the next step

Every start creates `artifacts/live/<session-id>/` containing:

| File | Content |
|---|---|
| `readings.csv` | Received, normalized, deduplicated rows with features, labels and inference results |
| `raw.jsonl` | Packet outcomes and heterogeneous payloads, including loss and duplicates |
| `manifest.json` | Seed, runs, steps, scenario, link assumptions, counters and completion status |

The download button returns a consistent snapshot of `readings.csv` even while it is growing. Download again for a later snapshot, or read the file after completion. Do not open the actively written file in an application that locks it against writing; use the download snapshot instead.

CSV columns:

```text
run_id,sensor_id,sequence,time_s,received_s,elapsed_s,arrival_elapsed_s,
scenario,protocol,distance_m,status,temperature_c,humidity_pct,smoke_ppm,
co_ppm,fire_present,drone_x_m,drone_y_m,probability,decision,reason
```

`time_s`/`received_s` are relative to a tour; `elapsed_s`/`arrival_elapsed_s` include earlier tours in the same session. The packet key is `(run_id,sensor_id,sequence)`. `fire_present` is simulator ground truth. `decision` and `probability` are model outputs: **never use these as target labels**. Train with the four features only. IDs, scenario, protocol, position and labels are audit metadata, not inputs to the supplied classifier.

Run IDs restart in every session. If combining session CSVs, add a session ID and split using `(session_id,run_id)` or remap run IDs globally. Avoid combining duplicate seeds/runs across splits. The current CLI intentionally trains from one session file.

## Create a training dataset through the live scene

Click **Prepare 15 mixed tours**, then **Start collection**. This selects normal/fire/nuisance, 15 tours and 64× speed. A tour represents 240 simulation seconds, so 15 tours nominally take about 56 seconds at 64×; CPU inference can make actual completion slower. Let the status become COMPLETED. Five runs per scenario is a minimal smoke test, not proof of real-world coverage. Use 90 or 300 mixed tours for larger experiments.

Then train from that specific completed session:

```powershell
uv run drone-train --input artifacts/live/SESSION-ID/readings.csv --output artifacts/live-training
```

Replace `SESSION-ID` with the directory displayed by the dashboard. The command checks required columns and at least five runs per scenario, then writes train/validation/test CSVs, model, metrics and decisions. It never uses the old predictions as targets. Use a new output directory for each experiment. A single fire demonstration tour does not meet the training requirement.

To view new collections using the newly trained model, stop the server and restart with `--model artifacts/live-training/model.joblib`.

## API

- `GET /api/state`: current state.
- `GET /api/events`: SSE state stream; browsers reconnect automatically.
- `POST /api/start`: JSON `{ "scenario": "mixed", "runs": 15, "steps": 120, "seed": 2026, "speed": 64 }`.
- `POST /api/stop`: gracefully stop collection.
- `GET /api/download/readings.csv`: a current complete-line snapshot.
- `GET /api/download/raw.jsonl` and `/api/download/manifest.json`: provenance downloads.

One collection can run at a time. Invalid ranges are rejected and a second simultaneous start returns conflict. This is a local classroom service; authentication, multi-user storage, durable queues and network deployment are outside its current scope.
