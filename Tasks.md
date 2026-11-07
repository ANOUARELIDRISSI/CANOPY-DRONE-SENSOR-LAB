# Drone monitoring project tasks

Start with the [collected readings](data/starter/readings.csv), [tour batches](data/starter/batches/) and [session manifest](data/starter/manifest.json). The starter session contains 589 synthetic readings across three tours. Use it to verify ingestion. Collect independent sessions across environments and weeks for model evaluation.

## Data engineering and storage

| Task | Purpose and output | Suggested technologies |
|---|---|---|
| 1. Archive raw data (Bronze) | Preserve original packets when available, delivered CSVs and manifests under `lake/bronze/ingest_date=YYYY-MM-DD/session_id=.../`. Record file hashes, seed, schema version, environment and collection time. Select one canonical input per session because the full CSV and tour files contain the same readings. | Local disk for Compose, S3-compatible object storage for shared runs, Python for manifests |
| 2. Stream completed tours | Publish each closed tour file into a watched directory by atomic rename. Process arriving files continuously, persist a checkpoint and recover after a restart. Compare the resulting reading keys against the session export. Keep SSE for live viewer updates. | Apache Spark Structured Streaming in local mode, Parquet file sink |
| 3. Clean and validate readings (Silver) | Create typed, standardized readings in `lake/silver/readings/`. Deduplicate by session, run, sensor and sequence. Preserve sample and arrival times, units, missingness and protocol. Quarantine invalid records with a reason and track late arrivals. Reconcile counts with Bronze. | PySpark DataFrames, Parquet, DuckDB SQL for audits |
| 4. Publish analytics and ML datasets (Gold) | Build tour, station, protocol and incident summaries in `lake/gold/analytics/`. Build versioned labeled snapshots in `lake/gold/ml/` from Silver. Keep observed features, label provenance and group identifiers distinct. Compute historical features from readings available by prediction time. | DuckDB SQL, Parquet, versioned snapshot manifests |

## Sensor models and seven-day training

| Task | Purpose and output | Suggested technologies |
|---|---|---|
| 5. Train a logistic regression baseline | Predict `fire_present` using temperature, humidity, smoke and CO. Split by whole sessions or tours, fit imputation and scaling on training data, and select the alert threshold on validation data. Exclude scenario, prior decisions, probabilities and IDs from predictors. | scikit-learn Pipeline and LogisticRegression |
| 6. Train an ensemble classifier | Train a random forest on the same features and splits. Compare fire recall, nuisance false alarms, precision, inference time and missed events against logistic regression. Record the model, threshold and dataset version together. | scikit-learn RandomForestClassifier, joblib |
| 7. Train a temporal CNN | Construct chronological windows per station within a single session and tour. Include missing-value masks and elapsed time. Predict fire at the window endpoint. Split before windowing so overlapping windows cannot cross partitions. Compare against both earlier models on the same eligible endpoints. | PyTorch CPU, small Conv1d network |
| 8. Run seven-day training batches | Every seven days, close an ingestion interval, validate new data and freeze a snapshot of eligible labeled tours. Train candidates on accumulated history, validate on later whole tours and reserve a separate test set for milestone evaluation. Record the cutoff, file hashes, split IDs, code version, seed and metrics. Late labels enter a subsequent version. Replaying a batch with identical inputs must reuse its identity. | Scheduled Python job or Airflow, Docker Compose training job, Parquet manifests, MLflow for model versions |
| 9. Evaluate and promote models | Compare the candidate and deployed model on the same recent labeled cohort held out from fitting. Check missed-fire rate, false alarms per tour, time to first alert and CPU latency. Promote only when agreed thresholds pass. Keep serving the current model if labels are insufficient or the candidate fails. Record the previous version for rollback. | scikit-learn metrics, MLflow Model Registry or a versioned model pointer |

## Vision, scoring and operations

| Task | Purpose and output | Suggested technologies |
|---|---|---|
| 10. Run computer vision alongside sensors | Run the existing CPU flame/smoke detector on selected-drone frames. Store frame ID, session, tour, drone, capture time, boxes, confidence, latency and model version. Evaluate visible flames, obscured fires and nuisance images. Track camera outages separately from frames with zero detections. | Existing YOLO fire detector, ONNX Runtime CPU, image files plus Parquet metadata |
| 11. Score incident evidence | Combine fresh station decisions with recent camera evidence from the same mission. Preserve the existing priorities: 3 for a fresh sensor alarm even with no visible flame, 2 for visual evidence alone, 1 for incomplete or stale sensor coverage, 0 for fresh clear readings. Log the reason, timestamps, model versions and estimated inspection area. | Existing JavaScript scoring engine, FastAPI, append-only decision records |
| 12. Build live and historical dashboards | Show fleet position, station age, sensor signals, camera availability and current alerts live. Query Gold for trends in protocol coverage, collection delay, class balance, false alarms and event detection latency by environment, week and model version. Link each alert back to its evidence. | Existing Three.js viewer and SSE, Streamlit, DuckDB |
| 13. Monitor data and service quality | Track missing channels, duplicate deliveries, ingestion lag, drift and CPU inference latency. Surface batch failures, schema changes and service outages. Exercise restart, replay and rollback with a recorded session. | Python validation checks, structured logs, Prometheus and Grafana if shared monitoring is needed |
| 14. Collect trajectories for later reinforcement learning | Log each simulated decision point: episode, step, observation available at that time, allowed actions, chosen action, policy version, next observation, elapsed time, termination or truncation and outcome. Record reward components such as detection delay, missed events and travel cost so rewards can be revised. Start with prescribed routes and distinguish observed actions from proposed alternatives. | Simulator event hooks, versioned Parquet trajectories under `lake/gold/rl/`, DuckDB for episode audits |

Streaming makes delivered tours available throughout the week. The seven-day job fixes the data cutoff for reproducible training. Live scoring continues with the deployed model while candidates train and are evaluated.
