# Real-Time Dashboard for Drone-Collected Data: Aggregation and Analytics

## 1. Project Summary

This project simulates a **drone that flies a predefined route over an area covered by wireless sensors**, collects their readings, aggregates the data, visualizes it on a real-time dashboard, and produces **recommendations** based on analysis and prediction.

A practical use case is **early detection of forest fires or flash floods**, where the system decides whether or not to trigger an alarm based on the predictions it makes.

## 2. Objectives

1. **Collect** data from wireless sensors distributed across a zone, using a drone on a collection tour.
2. **Aggregate** the data gathered from multiple sensors into a unified dataset.
3. **Visualize** the collected data in a real-time dashboard.
4. **Analyze and predict** events (e.g., fire or flood risk) and **recommend** actions, such as triggering an alarm.

## 3. System Overview

```
 Wireless sensors  ──►  Drone (predefined route)  ──►  Aggregation  ──►  Analytics / ML  ──►  Dashboard + Alarm decision
 (temp, humidity,        Bluetooth / WiFi /             (unified          (classification,      (Grafana or
  water level, ...)      proprietary protocol           dataset)           prediction)           similar)
```

### 3.1 Data Collection
- Sensors are spread over a monitored area.
- The drone follows a **predefined path**, so the focus is on the *sensor data itself*, not on spatio-temporal or geospatial analysis.
- Each drone-to-sensor link can use a different technology:
  - Bluetooth
  - WiFi
  - A proprietary protocol

### 3.2 Aggregation
- Merge readings from heterogeneous sensors and links into a consistent format.

### 3.3 Visualization
- A real-time dashboard shows the collected and aggregated data.
- **Grafana** is a suggested option for visualization and analysis.

### 3.4 Analysis and Recommendations
- Data analytics and prediction are the **core of the project**.
- **Python scripts** are sufficient, for example using **classification** approaches.
- Output: a recommendation, such as *"trigger the alarm"* or *"no alarm"*, based on the predicted risk of fire or flood.

## 4. Suggested Tools and Scope

| Area | Guidance |
|---|---|
| Simulation | **Gazebo** may be used as the simulation environment. |
| Drone stack | SITL, ArduPilot and Pymavlink are **not necessary**, since no real drones are involved. |
| Database | **TimescaleDB** and **PostGIS** are probably unnecessary, because the route is predefined and geospatial analysis is out of scope. |
| Analytics | Python scripts with classification-based prediction. |
| Visualization | Grafana (optional). |

## 5. Out of Scope

- Real drone hardware and flight-control protocols.
- Spatio-temporal / geospatial data analysis.
- Heavy infrastructure for time-series or GIS storage.

## 6. Key Focus

The emphasis is on **data aggregation, analysis, and prediction**, and on turning the results into a clear **decision** (alarm or no alarm) shown in a real-time dashboard.

The essential part is to **model the scenario well**. Concretely:

1. **Model the scenario** (e.g., forest fire or flash flood detection).
2. **Define the data to collect** (which sensor measurements are needed).
3. **Convert the data into variables and features**, starting from a dataset.
4. **Define the decision thresholds** that determine whether the alarm is triggered.

## 7. Implemented teaching baseline

The repository now contains a runnable forest-fire scenario: 12 stations, temperature/humidity/smoke-proxy/CO channels, three abstract wireless profiles, fixed-route collection, CSV normalization, run-separated training and two classifiers. The original scope above remains the project rationale.

The live 3D viewer displays the Crazyflie mesh from gym-pybullet-drones using Three.js. Server simulation time drives the drone position and sensor sampling. Arrived packets are normalized, classified, appended to CSV and published as state updates through server-sent events. This is prescribed motion and planar link modeling, not real radio traffic or aerodynamic physics. A separate Streamlit view replays recorded experiments.

See the [simulator guide](docs/SIMULATOR.md) for route planning, radio profiles and collection outputs.
