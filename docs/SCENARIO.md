# Scenario specification

## Scope and physical approximation

The model is a 2D collection experiment, not flight dynamics or a propagation simulator. Twelve stations lie on a 4 × 3 grid, 60 m apart. The closed lawnmower route passes all stations. There is no altitude, terrain, wind, collision avoidance, queue contention, interference or battery model. A default tour has 120 samples at 2 s intervals and finishes at 238 s. The same layout is used across runs; route geometry is visualization context, not an ML feature.

Each station has four channels:

| Canonical field | Unit | Normal model | Fire change after onset |
|---|---|---|---|
| `temperature_c` | °C | Run ambient N(25,5), station bias N(0,1.5), sample noise N(0,2) | +8 then growing +20–45 °C |
| `humidity_pct` | % | Run baseline uniform 40–75, sample noise N(0,4) | −5 then growing −25 points; clip to 0–100 |
| `smoke_ppm` | synthetic ppm proxy | max(0,N(4,2)) | +8 then growing +25–90 |
| `co_ppm` | ppm | max(0,N(0.7,0.4)) | +2 then growing +8–25 |

These distributions are teaching assumptions, not measured scientific ranges. Optical smoke sensors often report different quantities: do not equate a public sensor's raw output with ppm without calibration.

Runs cycle through `normal`, `fire`, `nuisance`. Onset is uniformly selected between approximately 20% and 50% of the tour. Six randomly selected stations are affected; severity grows linearly over 30% of the tour. The `fire_present` label becomes 1 at onset for affected stations in fire runs, including subtle early readings. A nuisance event adds smoke-proxy noise (+15–80) and some warmth (+0–7), but not combustion-level CO. Normal and nuisance labels remain 0. Each run has an independent seeded random generator.

## Links and payloads

| Profile | Range | Nominal bitrate | Base delay | In-range packet loss | Application encoding |
|---|---:|---:|---:|---:|---|
| bluetooth | 35 m | 125,000 bit/s | 25 ms | 8% | Integer hundredths °C and % |
| wifi | 100 m | 6,000,000 bit/s | 8 ms | 3% | Fahrenheit JSON, humidity % |
| proprietary | 160 m | 9,600 bit/s | 90 ms | 12% | Version 1 channel array, Kelvin and humidity fraction |

Four stations use each profile. Profiles approximate differences for experiments; they are not implementations or conformance tests of Bluetooth, IEEE 802.11 or a real proprietary protocol. They operate independently with no shared channel capacity. Arrival time = sample time + base delay + serialized JSON bytes × 8 / bitrate. The delay is a timestamp model, not a real socket delay. Reception eligibility is checked at sample time.

Samples outside range are logged as `out_of_range`, not link failures. In-range packets can be `lost`; otherwise `received`. No backlog is collected on a later visit. Approximately 2% of generated payloads have one missing channel; approximately 1% of received packets have a duplicate log entry. Log order is shuffled deliberately. Ground-truth metadata exists for evaluation but lost packets have no payload available to ingestion.

## Data contract

Raw JSONL envelope: `run_id`, `sensor_id`, `sequence`, `time_s`, `protocol`, `scenario`, `fire_present`, `distance_m`, `status`, `received_s`, `payload`.

`time_s` and `received_s` are seconds relative to the start of their run, not UTC. For non-received packets, `received_s` is a calculated potential arrival time and must never be interpreted as actual delivery. `(run_id, sensor_id, sequence)` is the sample key. The manifest carries seed, generator version, experiment size, counts and link configuration.

The normalized table retains envelope fields plus four canonical measurements. Bounds validation rejects non-finite non-missing values and values outside −50…150 °C, 0…100% RH, 0…1000 smoke proxy, and 0…500 CO ppm. These are schema guards, not alarm thresholds. Per-tour min/mean/max/count are exported for analysis but not used as predictive features: whole-tour summaries contain future data if used during an ongoing tour.

## Decisions and evaluation

The classifier detects current simulated fire presence; it does not forecast a future fire. The cutoff is selected on validation runs, with false negatives weighted five times false positives. Missing input yields WARNING at inference. Dashboard data older than 30 seconds is also WARNING. Dashboard ALARM takes precedence if another fresh station is alarming; otherwise incomplete coverage prevents a zone-level NO_ALARM.

`metrics.json` reports per-reading classifier metrics, including imputed readings. These differ from dashboard decisions, which abstain on missing input and incorporate staleness. There is no event-level detection latency or alarm persistence metric yet. Students must add those before claiming early warning performance. Perfect synthetic classification can indicate an easy generator rather than a deployable detector.
