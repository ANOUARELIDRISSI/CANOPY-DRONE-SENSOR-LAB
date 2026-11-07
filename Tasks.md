# Student assignment: from collected readings to a live fire alert

Start with [data/starter/readings.csv](data/starter/readings.csv), its [manifest](data/starter/manifest.json) and its [per-tour batches](data/starter/batches/). These are two representations of the same session: 2 drones, 3 mixed tours, 589 delivered readings. This is an inspection and streaming fixture, not enough independent tours for classifier evaluation. Read [the project overview](PROJECT_OVERVIEW.md) and [Python practices](python_skill.md). For Docker commands work at the repository root; for native uv commands work in simulation/.

| Assignment | Suggested technology | Evidence to submit |
|---|---|---|
| 1. Read a delivered sample | Python and pandas | Make a dictionary for every CSV column. Trace one station sequence through sample and arrival time, drone, protocol, four measurement units, synthetic label and prediction. Explain one missing value or sequence gap. |
| 2. Store the evidence | Original CSV files on disk; DuckDB SQL and Parquet for curated data | Preserve the manifest and keep raw files immutable. Ingest either the session CSV or the tour files. Verify that the three batches total 589 rows and their keys and values match the continuous CSV. Include session identity with run, sensor and sequence when combining sessions. Report missingness, duplicates, and received counts by protocol and scenario. Use the manifest for scheduled/lost counts; absence alone does not prove radio loss. |
| 3. Build a streaming consumer | Apache Spark Structured Streaming in local mode | Specify a schema. Replay one closed tour file at a time by atomic rename into a watched directory. Write Parquet with a persistent checkpoint outside that directory. Stop after two tours, restart with the same checkpoint, add the third. Compare row keys and counts with the batch import. Explain the difference between file micro-batches and the viewer's live SSE updates. |
| 4. Collect training and holdout tours | Docker Compose batch job and Python | Generate several mixed batches with different seeds; record seed, tour count, generator settings and class balance. Reserve a separate collection for robustness checks. Repeat with a changed environment using the live viewer. Explain why additional rows from the same tour are not independent experiments. |
| 5. Train and choose a fire classifier | scikit-learn logistic regression and random forest | Use only temperature_c, humidity_pct, smoke_ppm and co_ppm; target fire_present. Keep tours disjoint across train/validation/test; account for reused seeds across collections. Fit imputation on training only. Select the cutoff on validation using a stated cost for missed fires and false alarms. Freeze before testing. Report confusion matrix, precision, recall, F1 and nuisance false alarms. Compare against an always-no-fire baseline. |
| 6. Score live evidence | Existing sensor classifier, JavaScript scoring engine, SSE and Three.js | Demonstrate a sensor alarm with the camera unavailable or a negative image, a camera-only inspection, and stale sensor coverage. Record evidence, priority, station, elapsed time and explanation. Measure missed fire events, time to first alarm and false alarms per tour. Never substitute drone coordinates for verified fire coordinates. |
| 7. Investigate optional vision | Existing CPU ONNX Runtime detector from prasodium/edge-fire-detection | Compare a visible flame, a nuisance image, and an early or obscured event. Record frame source, detections, latency and disagreement with sensors. No visible flame is not proof of safety. Only matched drone frames contribute to the live priority. A second drone inspection request is a design extension: propose target station, reason, expiry and duplicate suppression. |
| 8. Reproduce and report | Git, pytest, Ruff, mypy, Docker Compose | Have a teammate reproduce the workflow from a fresh checkout. Submit commands, versions, manifests, tests and an illustrated report. State which results are synthetic, what failed, and what independent real data would be needed for validation. |

## Run the reference implementation
From the repository root:
~~~powershell
docker compose --profile camera up --build -d --wait
docker compose run --rm batch --runs 30 --steps 120
docker compose run --rm train --classifier logistic_regression --include-live
docker compose run --rm train --classifier random_forest --include-live
docker compose restart viewer
~~~
Record each fit's output path before training the next model. Restarting the viewer loads the most recently published model. New batch jobs choose a new seed by default. Do not train on the three-tour starter session alone. See the [Compose runbook](docs/COMPOSE.md) for file locations and camera instructions. DuckDB, Parquet ingestion and the Spark consumer are student implementations, not preconfigured services.


