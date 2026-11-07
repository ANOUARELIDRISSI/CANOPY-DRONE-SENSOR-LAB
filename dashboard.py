"""Run with uv run streamlit run dashboard.py -- artifacts/demo."""

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from drone_lab.simulation import LINKS, layout, route

st.set_page_config(page_title="Drone Sensor Lab", page_icon="🚁", layout="wide")
st.title("Drone Sensor Lab")
st.caption("Synthetic forest monitoring · fixed route · three simulated wireless links")
folder = Path(sys.argv[1] if len(sys.argv) > 1 else "artifacts/demo")
if not (folder / "decisions.csv").exists():
    st.info("Generate an experiment first: uv run drone-lab")
    st.stop()


@st.cache_data
def load(path: str):
    base = Path(path)
    return (
        pd.read_csv(base / "decisions.csv"),
        json.loads((base / "manifest.json").read_text()),
        json.loads((base / "metrics.json").read_text()),
    )


data, manifest, report = load(str(folder.resolve()))
with st.sidebar:
    st.header("Replay controls")
    scenario = st.selectbox("Scenario", ["normal", "fire", "nuisance"], index=1)
    candidates = data[data.scenario == scenario].run_id.unique().tolist()
    run = st.selectbox("Simulation run", candidates)
    autoplay = st.toggle("Play tour", value=False)
    start = st.slider("Start at sample", 0, manifest["steps"] - 1, 0)
    st.caption(
        "Replay advances two simulated seconds each second. "
        "This is recorded data, not live hardware."
    )
    st.write("Selected model:", report["selected_model"])
    st.caption("Gray stations are stale or not yet collected. Missing values produce WARNING.")


@st.fragment(run_every=1)
def replay():
    key = (run, start)
    if st.session_state.get("replay_key") != key:
        st.session_state.replay_key = key
        st.session_state.tick = start
    tick = st.session_state.tick
    now = tick * 2
    observed = data[(data.run_id == run) & (data.received_s <= now)]
    latest = observed.sort_values("received_s").drop_duplicates("sensor_id", keep="last").copy()
    latest["age_s"] = now - latest.time_s
    latest.loc[latest.age_s > 30, "decision"] = "WARNING"
    alarm_count = int((latest.decision == "ALARM").sum())
    a, b, c, d = st.columns(4)
    a.metric("Tour time", f"{now} s")
    b.metric("Stations seen", f"{len(latest)} / 12")
    c.metric("Received samples", len(observed))
    d.metric("Current alarms", alarm_count)
    if alarm_count:
        st.error("ALARM — synthetic fire signature detected; inspect affected stations.")
    elif len(latest) < 12 or (latest.decision == "WARNING").any():
        st.warning("WARNING — incomplete or stale coverage; recollect before concluding no alarm.")
    else:
        st.success("NO_ALARM — available fresh measurements are below the model cutoff.")
    left, right = st.columns([1, 1.2])
    with left:
        nodes, path = layout(), route(manifest["steps"])
        colors = {"ALARM": "#ef4444", "NO_ALARM": "#10b981", "WARNING": "#94a3b8"}
        states = dict(zip(latest.sensor_id, latest.decision))
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.plot(path[:, 0], path[:, 1], "--", color="#cbd5e1")
        ax.plot(path[: tick + 1, 0], path[: tick + 1, 1], color="#2563eb")
        for i, (x, y) in enumerate(nodes):
            ax.scatter(x, y, color=colors[states.get(i, "WARNING")], s=100)
            ax.annotate(f"{i} {list(LINKS)[i % 3]}", (x, y + 7), fontsize=7, ha="center")
        ax.scatter(*path[tick], marker="X", color="#2563eb", s=180, label="Drone")
        ax.set(xlim=(-10, 230), ylim=(-10, 175), xlabel="x (m)", ylabel="y (m)")
        ax.legend()
        st.pyplot(fig)
        plt.close(fig)
    with right:
        st.subheader("Received measurements")
        if observed.empty:
            st.info("Waiting for the first packet to arrive.")
        else:
            st.line_chart(
                observed.groupby("time_s")[["temperature_c", "smoke_ppm", "co_ppm"]].mean()
            )
        st.caption("Mean over stations received at each time; measurements use different units.")
    st.dataframe(
        latest[
            [
                "sensor_id",
                "protocol",
                "temperature_c",
                "humidity_pct",
                "smoke_ppm",
                "co_ppm",
                "age_s",
                "probability",
                "decision",
            ]
        ],
        hide_index=True,
        use_container_width=True,
    )
    if autoplay and tick < manifest["steps"] - 1:
        st.session_state.tick = tick + 1


replay()
with st.expander("Held-out evaluation and experiment overview"):
    st.json(report["models"])
    st.image(str(folder / "overview.png"))
    st.caption(
        "Metrics evaluate synthetic-generator labels only. "
        "They do not establish real-world fire detection accuracy."
    )
