# Drone fire monitoring lab
Start with [the student assignment](Tasks.md) and [the collected session](data/starter/manifest.json). This is a synthetic monitoring experiment. The simulator knows when a fire starts; the student classifier is only allowed to observe delivered measurements.

Stations measure temperature, humidity, smoke and CO. A predefined fleet route and three abstract radio profiles determine which readings reach a drone. Normalization produces one row per delivered sample. The viewer streams updates over SSE, appends rows to a session CSV and exports separate tour files. Randomized collections can then train a sensor classifier. The seed and manifest let a team reproduce a run.

The viewer's scoring engine assigns an ordinal inspection priority, not a probability: 3 = fresh sensor alarm (even without visible smoke); 2 = recent flame/smoke detection from the selected drone without a sensor alarm; 1 = incomplete sensor coverage; 0 = fresh sensors below threshold. Vision alone does not locate a fire. Manual uploads, sample photos and webcam tests never affect fleet scoring. Current drone evidence expires after five seconds of wall or simulation time, or on a change of tour. Station readings older than 30 simulation seconds are stale.

| Location | Purpose |
|---|---|
| simulation/ | Python source, 3D assets, tests, lockfiles and native entry points |
| Dockerfile and compose.yaml | Build and run from the repository root |
| data/starter/ | Completed synthetic session distributed for the first exercises |
| artifacts/ | Local Compose outputs: new batches, live sessions and trained models |
| python_skill.md | Python engineering practices for students |
| docs/ | [How the simulator works](docs/SIMULATOR.md) |

Run from the repository root: docker compose --profile camera up --build -d --wait. Open http://127.0.0.1:8765. Omit the camera profile for sensor-only operation. Native Python development commands run inside simulation/. Native outputs are relative to that directory unless an explicit output path is supplied.

The scoring panel is a field-wide summary. Use the station table to identify a sensor alarm; drone coordinates describe the collector, not the source of a fire. The simulation does not dispatch an emergency service or autonomously extinguish fires.
