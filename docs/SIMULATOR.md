# How the drone simulator works

From the repository root run `docker compose up --build -d`, open http://127.0.0.1:8765, choose the environment, preview the fleet and start collection. The live viewer supports 1–8 drones and 6–60 stations. Forest, meadow and desert change the synthetic temperature and humidity baseline. Vegetation changes the scenery.

## How the tour is planned

The simulator uses a **lawnmower sweep** across a rectangular grid. It visits the first row left to right, reverses direction on the next row, and alternates until the final station. A straight segment closes the tour. With twelve stations numbered from zero, the route is:

`0 → 1 → 2 → 3 → 7 → 6 → 5 → 4 → 8 → 9 → 10 → 11 → 0`

The resulting graph is a cycle: each station is a vertex and consecutive waypoints are joined by straight edges. The grid fixes the order without a shortest-path search. The simulator adds the Euclidean lengths of the edges, then interpolates coordinates at equal distances along the circuit. See the [live fleet planner](../simulation/src/drone_lab/environment.py) and [fixed batch route](../simulation/src/drone_lab/simulation.py).

## How the drones move

Every drone follows the same circuit in the same direction, starting at a different offset. The offsets space the fleet approximately evenly around the route. Each drone completes one lap per tour and returns to its starting point. Samples are two simulated seconds apart. For a fixed field, increasing the steps per lap increases its duration and decreases the drone's speed. Playback speed controls how quickly those simulated seconds pass on screen. The 3D altitude is illustrative; radio distance uses horizontal coordinates in metres.

## How stations transmit readings

Each station measures temperature, relative humidity, smoke and carbon monoxide. Station IDs cycle through the following profiles. The simulator implements one abstract Bluetooth profile; the numbers below are simulation parameters.

| Profile | Maximum range | Bit rate | Base delay | In-range packet loss | Payload |
|---|---:|---:|---:|---:|---|
| Bluetooth | 35 m | 125 kb/s | 25 ms | 8% | Temperature and humidity in hundredths |
| Wi-Fi | 100 m | 6 Mb/s | 8 ms | 3% | Fahrenheit and percent humidity |
| Proprietary | 160 m | 9.6 kb/s | 90 ms | 12% | Kelvin and fractional humidity |

At each sample a station attempts transmission to its nearest drone. A distance greater than the profile range produces an out-of-range record. Within range, the profile's loss probability applies. Successful delivery takes the base delay plus the serialized payload size in bits divided by its bit rate. For example, at 50 m a Bluetooth station is out of range while a Wi-Fi station can transmit.

## What collection produces

Use **Download CSV** for one file containing all delivered readings, or open `artifacts/live/<session>/readings.csv`. Each row identifies the station, collecting drone, protocol, distance, sample and arrival times, normalized measurements and synthetic fire label. The service also saves the raw transmission log, session manifest and per-tour CSVs. The per-tour files contain the same readings as the full CSV. Import one representation to avoid double counting.

The viewer renders a [Crazyflie mesh](https://github.com/learnsyslab/gym-pybullet-drones) with Three.js. The optional camera's unmodified reference photograph comes from [LibreYOLO/fire-smoke-seg](https://huggingface.co/datasets/LibreYOLO/fire-smoke-seg) under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
