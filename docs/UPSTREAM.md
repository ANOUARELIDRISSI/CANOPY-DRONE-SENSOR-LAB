# UavNetSim investigation

Native Python and npm commands in this guide run from the `simulation/` directory.

Source: [Zihao-Felix-Zhou/UavNetSim](https://github.com/Zihao-Felix-Zhou/UavNetSim). The older `UavNetSim-v1` URL redirects to this project. The tested checkout is `c2703f24eb58cdb557a5f67ded5c7b0368a964ed`, package version 2.0.0, MIT license. Its current purpose is UAV network simulation; it does not provide this lab's sensor-fire dataset pipeline out of the box.

The local checkout is under ignored `external/UavNetSim-v1`; no upstream source has been copied into the teaching package. The main lab does not import it. Its own environment is separate from the lab environment.

## Reproduce the optional smoke test (PowerShell)

```powershell
git clone https://github.com/Zihao-Felix-Zhou/UavNetSim.git external/UavNetSim-v1
git -C external/UavNetSim-v1 checkout c2703f24eb58cdb557a5f67ded5c7b0368a964ed
cd external/UavNetSim-v1
uv venv --python 3.12 .venv
uv pip install --python .venv/Scripts/python.exe -e .
.venv/Scripts/python.exe main.py compile-scene scenarios/default_scene.json --output artifacts/scene --no-osm2world
.venv/Scripts/python.exe -c 'from utils import config; config.CHANNEL_MODE="a2a"; from main import parser; args=parser().parse_args(["run","--nodes","3","--duration","5","--seed","42"]); args.handler(args)'
```

Test result on this Windows machine: install succeeded; scene compilation succeeded; analytical `a2a` mode exited 0, sent 74 packets, reported 100% delivery, 6.7073 ms average end-to-end delay, and 11 collisions. This small smoke test is not a statistical networking benchmark. Upstream dependencies are not locked by the teaching package's `uv.lock`.

The default command was also attempted:

```powershell
.venv/Scripts/python.exe main.py run --nodes 3 --duration 2 --samples 1000
```

It failed at Sionna/Dr.Jit initialization because `LLVM-C.dll` could not be found. The upstream error suggests `DRJIT_LIBLLVM_PATH`. The analytical-mode command avoids that backend without modifying upstream source. Ray tracing, the upstream frontend, PyBullet, Gazebo and real radios were not validated. Installing a larger simulation stack is optional and should not block the core aggregation and analytics assignment.

The original task plan described a smaller pure-SimPy starter. The current checkout has a broader dependency stack, including Sionna RT and Mitsuba; students should use the pinned commit and explicit analytical mode if choosing this extension.
