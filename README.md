# Canopy Drone Sensor Lab

Canopy lets you build a 3D drone simulation that collects environmental readings as a fleet flies over sensor stations. You can follow the flight live and download the measurements each drone receives.

| What you can build | How it works |
|---|---|
| A configurable 3D field | Choose a forest, meadow or desert, place 6–60 stations on a grid, and run one or more tours with up to eight drones. |
| A fleet collection demo | Drones start at different points on the same zigzag circuit. Select a drone, follow it around the field, and zoom in as it passes a station. |
| A wireless coverage experiment | Each station attempts to send temperature, humidity, smoke and carbon monoxide readings to the nearest drone. Compare delivery across simulated Bluetooth (35 m), Wi-Fi (100 m) and proprietary radio (160 m) as you vary fleet size or field width. |
| A live sensor dataset | Watch readings arrive during a flight. Download one CSV per session with the tour, station, collecting drone, protocol, distance, sample and arrival times, and measurements. |
| A repeatable scenario comparison | Run normal, fire and nuisance scenarios. Record the seed and field settings, then change one setting at a time to compare readings and coverage across tours. |

## Run a collection

From the repository root, run `docker compose up --build -d --wait` and open the [3D viewer](http://127.0.0.1:8765). Preview the field, start collection, and use **Download CSV** after the last tour. The full session is saved locally to `artifacts/live/<session>/readings.csv`.

## Experiment: detecting a fire with unreliable coverage

Use the same seed and field layout for two flights, then change the number of drones. Compare the time from simulated fire onset to the first delivered alarm and count missed events. Use the session raw log to count lost and out-of-range attempts by protocol. The readings CSV contains only delivered packets.

The `protocol` column identifies Bluetooth, Wi-Fi or the proprietary link. Each profile sets its range, loss probability, base delay and bitrate. Compare `distance_m` with `link_range_m` for coverage and use `delivery_delay_ms` for latency. About 2% of simulated samples omit one randomly chosen measurement. A delivered packet with a missing measurement has a literal `NaN` in that sensor column and the live classifier returns WARNING. A whole packet that fails to arrive produces no readings row. These parameters are synthetic assumptions.

The viewer renders a [Crazyflie drone mesh](https://github.com/learnsyslab/gym-pybullet-drones) using Three.js. The optional camera view includes an unmodified reference photograph from [LibreYOLO/fire-smoke-seg](https://huggingface.co/datasets/LibreYOLO/fire-smoke-seg), licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
