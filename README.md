# Canopy drone simulator

Build a 3D field, follow a drone around its tour, and export the sensor readings it receives. Each station measures temperature, humidity, smoke and carbon monoxide. A fleet can collect multiple tours in one session.

## Build and open the viewer

With Docker Compose running, use these commands from a terminal:

~~~sh
git clone --branch main https://github.com/ANOUARELIDRISSI/CANOPY-DRONE-SENSOR-LAB.git
cd CANOPY-DRONE-SENSOR-LAB
docker compose up --build -d --wait
~~~

Open the [3D viewer](http://127.0.0.1:8765). Choose an environment, set the number of drones and tours, then preview the field. Start collection, select a drone and use **Follow** to track it. Scroll to zoom or drag to orbit.

## Collect a CSV

Use **Download CSV** during a flight to inspect readings delivered so far, or after the final tour for the full session. Compose also saves the file to `artifacts/live/<session>/readings.csv` on the host. For an example from a completed flight, open the [sample CSV](data/starter/readings.csv).

Follow the [collection checklist](Tasks.md) for a reproducible run. The [simulator guide](docs/SIMULATOR.md) explains the route, fleet movement, radio ranges and output files. To stop the containers, run `docker compose down` from the repository root.
