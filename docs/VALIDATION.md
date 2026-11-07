# Validation record — 7 November 2026

Executed locally on Windows with Python 3.12.4 and uv. Exact Python dependencies are in `uv.lock`; Three.js is pinned by `package-lock.json` and vendored into the viewer. Results below are measured, not expected targets.

## Batch generation and training

```powershell
uv sync --locked --all-groups
uv run drone-lab --runs 90 --steps 120 --seed 42 --output artifacts/demo
uv run drone-lab --runs 300 --steps 120 --seed 2026 --output artifacts/experiment-2026
```

| Measurement | 90 tours, seed 42 | 300 tours, seed 2026 |
|---|---:|---:|
| Scheduled sensor samples | 129,600 | 432,000 |
| Unique received CSV rows | 58,442 | 195,032 |
| Out of range | 65,610 | 218,700 |
| Lost in range | 5,548 | 18,268 |
| Extra duplicate log rows | 598 | 1,933 |
| Training rows | 35,064 | 117,004 |
| Validation rows | 11,725 | 39,070 |
| Test rows | 11,653 | 38,958 |
| Selected model | Random forest | Random forest |
| Selected cutoff | 0.45 | 0.80 |
| Test precision | 0.997928 | 1.000000 |
| Test recall | 1.000000 | 0.999563 |
| Test F1 | 0.998963 | 0.999781 |

The first test confusion matrix is `[[10205,3],[0,1445]]`; the larger experiment is `[[34386,0],[2,4570]]`. Rows are true no-fire/fire and columns predicted no-fire/fire. Logistic regression was also fitted and evaluated; see the generated `metrics.json` files.

The 90-tour validation learning curve used 12, 27 and 54 training runs (7,782 / 17,543 / 35,064 rows). F1 was 0.996466 / 0.997642 / 0.999606. These strong scores mainly demonstrate that this generator is easily separable. They do not establish sufficient data for real fire detection.

## Live 3D collection → CSV → model

1. Started the local service with `uv run python -m drone_lab.server --port 8765`.
2. Opened the viewer in a browser and verified that the cloned Crazyflie mesh loads, moves along the tour, and is visible in follow mode. Sensor markers, transmission lines, telemetry and ALARM updates rendered.
3. A fire demonstration completed with 657 received rows. During collection, the CSV was inspected while still open: 339 complete rows, all three link types, no duplicate keys, and latest arrival time earlier than the simulation clock.
4. An initial accelerated test exposed excessive cost from one-at-a-time model inference. The implementation now batches arrived packets. The superseded partial session `20261107-002115-7813d731` is marked interrupted and is excluded from results.
5. The corrected service completed 15 mixed tours, 120 steps, seed 2026, speed 64×, in **57.48 wall-clock seconds**.

Successful session: `artifacts/live/20261107-002458-5f727f53/`.

| Live dataset property | Observed |
|---|---:|
| Unique received rows | 9,762 |
| Bluetooth rows | 677 |
| WiFi rows | 3,620 |
| Custom-link rows | 5,465 |
| No-fire labels | 8,842 |
| Fire labels | 920 |
| Independent runs per scenario | 5 |
| In-range lost samples | 903 |
| Out-of-range samples | 10,935 |
| Extra duplicate raw log entries | 83 |

The actual next-step command succeeded:

```powershell
uv run drone-train --input artifacts/live/20261107-002458-5f727f53/readings.csv --output artifacts/live-training
```

It trained both classifiers and selected random forest using validation only. Its 1,948-row test set produced `[[1726,0],[0,222]]`. This is a small synthetic smoke test; a perfect score is not a real-world performance claim. `artifacts/live-verification.json` records growing-row observations and final state.

## Automated checks

`uv run ruff check .`, `uv run ruff format --check .`, and `uv run mypy src` pass. **14 pytest tests pass**, covering:

- Conversion between all payload representations and missing-value handling.
- Route coverage, range gating, statistical link loss and timestamp ordering.
- Deduplication, deterministic generation, disjoint run splits and two-model training.
- Normal/fire/missing-input decisions and invalid configuration.
- Live CSV growth while open, arrival-time gating and graceful close.
- Exact live-versus-batch feature/label equality across 15 mixed runs.
- No stale readings carried as fresh into a new tour.
- API validation, concurrent-start rejection, start/stop, downloads and 3D asset availability.

There is one upstream Starlette test-client deprecation warning concerning httpx; it does not fail the tests. Test scratch directories are created inside the project because this machine's default pytest temporary directory denied access. `node --check src/drone_lab/web/app.js` passes. `uv build` successfully produced a source distribution and wheel; the wheel was inspected and contains the viewer, Crazyflie mesh and all required loaders.

The Streamlit replay and exported overview image were also inspected. The live 3D viewer is the main answer to the request for a moving drone, not the earlier 2D plot. [Saved visual evidence](screenshots/live-drone.png).

## External repositories

- UavNetSim: install and scene compilation succeeded; analytical `a2a` mode completed a 3-drone, 5-second smoke test, reporting 74 sent packets and 100% delivery. Default online Sionna mode failed because LLVM-C.dll is absent. Exact revision/commands are in [UPSTREAM.md](UPSTREAM.md).
- gym-pybullet-drones: cloned and its Crazyflie mesh integrated and rendered in the browser. Its full Gym/PyBullet controller and physics stack were not installed or claimed tested. Source revision and MIT attribution are in [THIRD_PARTY.md](THIRD_PARTY.md).

## Remaining limits

Sensor distributions, radio ranges/loss and nuisance mechanisms are classroom assumptions. The 3D scene uses prescribed motion, enlarged geometry and an illustrative altitude; links use planar distance. No real radios, real sensor calibration, aerodynamic physics, forecast horizon, independent measured dataset, event-level detection-latency study or production deployment was validated. SSE publishes the latest state rather than a durable packet stream; the CSV is the complete delivered-reading record. On abrupt process termination, a session may be partial and must not be treated as completed.

This validation was performed locally before publishing the source on branch `anouar00`. Generated data and trained models remain local and are reproduced with the documented commands. No public application deployment was performed.
