# Simulation and collection checklist

Follow the [build instructions](README.md) to start the viewer. Use the [simulator guide](docs/SIMULATOR.md) to interpret the tour and radio behavior.

1. Open the viewer and preview a field. Record the environment, seed, station count, drone count, tours and steps per tour.
2. Start collection with two drones. Select each drone in turn, use Follow and zoom, and observe their different starting positions on the same circuit.
3. Watch the received counts for Bluetooth, Wi-Fi and proprietary stations. Identify one delivered reading and record its station, collecting drone, protocol and distance.
4. When the session completes, download its CSV. Compare its row count with the received count shown in the viewer. Inspect sample time and arrival time for one station.
5. Compare the session CSV with the per-tour files in the same session folder. Their combined data-row count should equal the session total. Use the manifest to check the seed and counts of lost and out-of-range transmissions.
6. Repeat the same configuration and seed to reproduce a run. Then change one setting, such as fleet size, and compare received counts per protocol.
