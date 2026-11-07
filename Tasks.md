# Student task guide: drone-collected sensor data

## Assignment and baseline

Build and explain a system in which a drone follows a predefined route, collects heterogeneous sensor readings, normalizes them, classifies current fire presence, and displays a recommendation. The focus is scenario modeling, data quality, analytics and evaluation. Flight control and geospatial analysis are outside the required scope.

This repository supplies a runnable reference implementation. Reproduce it, explain its assumptions, then extend it. Checkboxes below are student work, not claims that every extension is implemented. See [VALIDATION.md](docs/VALIDATION.md) for measured results.

**Implemented:** 12 stations with four measurement channels, fixed 2D tour, three abstract wireless profiles, normal/fire/nuisance scenarios, packet loss, missing values, duplicates, normalization, grouped splits, two classifiers, plots, dashboard replay, a 3D drone scene and live CSV/SSE streaming.

**Extensions still to do:** real-data validation, harder confounders, event-level latency evaluation, alternate layouts and flood detection. Real radios and 3D flight physics are optional.

## Phase 1 — Understand and reproduce

- [ ] Read [PROJECT_BRIEF.md](PROJECT_BRIEF.md), [README.md](README.md) and [SCENARIO.md](docs/SCENARIO.md).
- [ ] Explain the difference between a measurement channel, sensor station, application payload and wireless link model.
- [ ] Assign owners for simulation, aggregation, analytics and dashboard. Every member must run the complete workflow.
- [ ] Clone branch `anouar00` using the exact command in the README. The default branch may not contain this teaching version.
- [ ] Install Git and uv, then run from the project root:

```powershell
uv sync --locked --all-groups
uv run drone-lab --runs 90 --steps 120 --seed 42 --output artifacts/demo
uv run streamlit run dashboard.py --server.address 127.0.0.1 -- artifacts/demo
```

- [ ] Use a new output directory for another experiment; existing nonempty directories are protected.
- [ ] Open the dashboard, choose fire, move the slider, and play the tour. Explain initial WARNING coverage.
- [ ] Read [the Python skill](.agents/skills/python-production/SKILL.md) and its linked full guide. Follow the existing uv/Ruff/mypy/pytest workflow without installing every tool in the reference.

**Deliver:** environment versions, command transcript, manifest, overview image and a diagram explaining the pipeline.

**Done when:** each student can produce data and open the dashboard without editing absolute paths. The reference configuration schedules 129,600 samples and collects 58,442 unique readings.

## Phase 2 — Defend the scenario and collection model

- [ ] Trace `layout()`, `route()`, `generate()` and `LINKS` in `src/drone_lab/simulation.py`.
- [ ] Verify the route visits all 12 stations within their assigned ranges; identify four stations per profile.
- [ ] Explain units and normal/fire distributions. Synthetic smoke ppm cannot be equated with raw optical sensor output without calibration.
- [ ] Explain why labels come from latent scenario state, not measured-feature thresholds.
- [ ] Add one harder nuisance case, such as strong heat without fire, and document its physical assumptions.
- [ ] Calculate arrival delay from payload bytes, bitrate and base delay. Explain the absence of shared-channel interference, queues and retries.
- [ ] Calculate in-range loss per protocol. Do not count out-of-range samples as packet loss.
- [ ] Vary one link assumption and compare coverage while holding seed and steps fixed. Note that RNG branching can alter downstream noise: this is not a fully paired causal experiment.

**Deliver:** revised scenario document, route figure, link comparison and behavior test for the new case.

**Done when:** all three profiles appear in received data, loss denominators are correct, and the report clearly identifies the profiles as simulations rather than real Bluetooth/WiFi implementations.

## Phase 3 — Audit aggregation and data quality

- [ ] Trace `encode()` and `decode()`. Test Celsius/Fahrenheit/Kelvin and humidity-fraction conversion.
- [ ] Reconcile received, lost, out-of-range and duplicate counts. Duplicates are additional log rows, not additional scheduled readings.
- [ ] Verify unique `(run_id, sensor_id, sequence)` keys and ascending sample time within each sensor/run.
- [ ] Inspect missing values. Explain training-only imputation and why lost payloads are never reconstructed from simulator ground truth.
- [ ] Report class, scenario, sensor and protocol counts for each split. Plot feature distributions and identify overlapping early-fire/nuisance readings.
- [ ] Examine per-tour count/mean/min/max in `tour_summary.csv`. If adding rolling features, use only readings already received at prediction time. Whole-tour statistics leak future data into earlier predictions.
- [ ] Add a malformed-payload test establishing the intended rejection policy.

**Deliver:** data-quality report, unit/feature dictionary, distributions, missingness summary and provenance.

**Done when:** aggregation is reproducible; labels, scenario names and IDs never enter the predictor; temporal features cannot use future values.

## Phase 4 — Train, evaluate and assess data sufficiency

- [ ] Explain the 60/20/20 split by whole runs within each scenario. Verify disjoint train/validation/test run IDs.
- [ ] Compare logistic regression and random forest using accuracy, precision, recall, F1 and a confusion matrix. Explain why accuracy alone is insufficient.
- [ ] Explain or justify changing the classroom validation cost `5 × missed fires + false alarms`.
- [ ] Choose the model/cutoff on validation only; freeze the choice before inspecting test scores.
- [ ] Interpret per-scenario results. For all-negative normal/nuisance groups, count false positives rather than interpreting fire recall/F1.
- [ ] Discuss the validation learning curve in `metrics.json`. It is a small diagnostic using the selected cutoff, not a confidence interval.
- [ ] Generate a larger independent experiment:

```powershell
uv run drone-lab --runs 300 --steps 120 --seed 2026 --output artifacts/experiment-2026
```

- [ ] Keep `--steps` fixed in dataset-size comparisons: changing it changes tour duration and drone speed.
- [ ] Explain that this command retrains. For a frozen-model robustness test, score new readings with the original model without refitting; do not call a newly trained score validation of the original model.
- [ ] Repeat seeds and report variation. Hold out changed environments, layouts or nuisance mechanisms, not just more rows from the same generator.
- [ ] Assess one independently measured dataset: source URL, version, license, units, labels, sensor compatibility and missingness. Download only if access and license allow. Restricted or incompatible datasets are not required dependencies.
- [ ] Explain why near-perfect synthetic accuracy may reveal an easy generator. Specify the independent evidence needed before claiming sufficient real-world training data.

**Deliver:** model comparison, split manifest, learning-curve discussion, frozen-model robustness results and real-dataset suitability assessment.

**Done when:** a reviewer can reproduce scores and verify no run leakage. More generated rows alone do not satisfy this phase.

## Phase 5 — Decisions and visual demonstration

- [ ] Trace `predict()`: complete normal/fire inputs yield NO_ALARM/ALARM; missing input yields WARNING.
- [ ] Capture normal, fire and nuisance dashboard runs with run ID and time visible.
- [ ] Explain station colors, collection age and the probability cutoff. Unvisited/stale coverage must not silently become NO_ALARM.
- [ ] Explain that `dashboard.py` is the Streamlit replay of `decisions.csv`, while `drone-live` is the live 3D producer/consumer service.
- [ ] Run `uv run drone-live`, open localhost:8765 and inspect the 3D drone with **Follow drone**. Read [LIVE_3D.md](docs/LIVE_3D.md) and trace `SensorTour`, the arrival queue, frozen-model inference, CSV flush and SSE snapshots.
- [ ] Click **Prepare 15 mixed tours**, collect to completion, and run `uv run drone-train --input artifacts/live/SESSION-ID/readings.csv --output artifacts/live-training`. Explain why one fire demonstration tour is insufficient.
- [ ] Verify that downloading CSV during a live run returns only complete delivered rows. Reconnect the browser and confirm collection continues; test stop/shutdown behavior.
- [ ] Test that future packets are never shown early and duplicates never accumulate.
- [ ] Add event-level detection latency, missed-event rate and false alarms per tour. Distinguish them from per-reading classifier metrics.
- [ ] Add alarm persistence/recovery if appropriate and test behavior after an event ends.

**Deliver:** three scenario captures, replay demo, live 3D streaming demo, training CSV and event-level evaluation.

**Done when:** arrivals visibly update the dashboard and students can distinguish ground truth, prediction and recommendation.

## Phase 6 — Engineering and handoff

```powershell
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest -q
```

- [ ] Run all checks and resolve failures. Test scratch files live in unique `artifacts/tests/run-*` directories.
- [ ] Commit source/tests/docs, `pyproject.toml`, `.python-version` and `uv.lock`; exclude environments, secrets, generated data and external clones.
- [ ] Record seeds, configurations and metric reports for every reported experiment.
- [ ] Add CI for these checks if submitting on GitHub. Pin reviewed third-party actions and use minimal permissions.
- [ ] Write a report covering problem, assumptions, architecture, link abstractions, provenance, split strategy, models, results and limitations.
- [ ] Ask another student to reproduce from a fresh checkout, then prepare a five-minute demo.

**Deliver:** reviewed repository, reproducible results, report and presentation.

**Done when:** a new student can reproduce the demo and explain why it is a teaching/research prototype rather than a validated fire alarm.

## Optional networking and 3D work

After the core pipeline works, follow [UPSTREAM.md](docs/UPSTREAM.md) to clone the pinned UavNetSim revision and run analytical mode. Its default ray-tracing mode failed on the instructor machine due to missing LLVM; it is not a prerequisite. Compare its network model with this lab's abstractions and preserve its license.

The cloned gym-pybullet-drones mesh is already integrated into the 3D viewer; its physics/control environment is not. Full PyBullet/Gazebo dynamics, MQTT/HTTP ingestion, real Bluetooth/WiFi adapters, flooding, additional drones and battery models are separate extensions. MQTT/HTTP are application protocols and do not replace the distinction between wireless link technologies. Claim implementation/testing only when there is evidence.
