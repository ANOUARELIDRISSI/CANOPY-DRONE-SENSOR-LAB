# Third-party assets

## Crazyflie drone mesh

- Repository: https://github.com/learnsyslab/gym-pybullet-drones
- Tested source revision: `348b5c18a4bb770a48928b9d044decf77ca33302`
- Source asset: `gym_pybullet_drones/assets/cf2.dae`
- Local asset: `src/drone_lab/web/assets/cf2.dae`
- License: MIT, retained verbatim in `assets/LICENSE.gym-pybullet-drones`.
- The asset's internal COLLADA metadata credits Lakshman Kumar.

The repository was cloned to ignored `external/gym-pybullet-drones`. This project uses its actual 3D mesh. It does not import the repository's Gym environment, PID controller or PyBullet physics engine. The displayed drone follows the prescribed collection route; the model is enlarged for visibility and altitude is illustrative. Do not describe this as validated aerodynamic simulation.

## Three.js

- Package: `three`, version `0.180.0`, MIT license.
- `package-lock.json` locks the npm package and integrity hash.
- `scripts/vendor-three.mjs` copies the runtime, OrbitControls, ColladaLoader, TGALoader and license into the Python package's `web/vendor` directory.
- Files are included locally so students do not need a CDN or npm to run the viewer.

To refresh the vendored files deliberately: `npm ci --ignore-scripts`, then `npm run vendor`. Review and retain the licenses. On the tested Windows computer the npm wrapper was misconfigured; invoking Node directly with `C:\Program Files\nodejs\node_modules\npm\bin\npm-cli.js` worked. This workaround is unnecessary on a normal Node installation.

UavNetSim remains a separately cloned optional networking experiment; see [UPSTREAM.md](UPSTREAM.md).
