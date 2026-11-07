"""Export reproducible route, signals, link quality and evaluation figures."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from drone_lab.simulation import LINKS, layout, route


def render(output: Path, manifest: dict, report: dict) -> None:
    readings = pd.read_csv(output / "decisions.csv")
    fig, axes = plt.subplots(2, 2, figsize=(13, 9), layout="constrained")
    fig.suptitle("Drone Sensor Lab | Synthetic experiment", fontsize=19, weight="bold")
    path, nodes = route(manifest["steps"]), layout()
    ax = axes[0, 0]
    ax.plot(path[:, 0], path[:, 1], "--", color="#64748b", label="Fixed tour")
    for i, protocol in enumerate(LINKS):
        indices = list(range(i, 12, 3))
        ax.scatter(nodes[indices, 0], nodes[indices, 1], s=75, label=protocol)
    for i, (x, y) in enumerate(nodes):
        ax.annotate(str(i), (x + 3, y + 5))
    ax.set(title="12 stations / 4 measurements per station", xlabel="x (m)", ylabel="y (m)")
    ax.set_xlim(0, 225)
    ax.set_ylim(0, 165)
    ax.legend(fontsize=8)
    ax = axes[0, 1]
    for scenario, group in readings.groupby("scenario"):
        example = group[group.run_id == group.run_id.min()]
        trend = example.groupby("time_s").smoke_ppm.mean()
        ax.plot(trend.index, trend.values, label=scenario)
    ax.set(
        title="Received smoke readings (one tour per scenario)",
        xlabel="Simulation time (s)",
        ylabel="Mean smoke proxy (ppm)",
    )
    ax.legend()
    ax = axes[1, 0]
    raw = pd.read_json(output / "raw.jsonl", lines=True)
    raw = raw.drop_duplicates(["run_id", "sensor_id", "sequence"])
    pd.crosstab(raw.protocol, raw.status).reindex(list(LINKS)).plot.bar(
        stacked=True, ax=ax, rot=0, color=["#ef4444", "#94a3b8", "#10b981"]
    )
    ax.set(title="Link outcomes (out of range is not packet loss)", ylabel="Samples")
    ax = axes[1, 1]
    winner = report["selected_model"]
    matrix = report["models"][winner]["test"]["confusion_matrix"]
    ax.imshow(matrix, cmap="Blues")
    for i in range(2):
        for j in range(2):
            ax.text(
                j,
                i,
                str(matrix[i][j]),
                ha="center",
                va="center",
                fontsize=20,
                color="white" if matrix[i][j] > max(map(max, matrix)) / 2 else "black",
            )
    ax.set(
        xticks=[0, 1],
        yticks=[0, 1],
        xticklabels=["No fire", "Fire"],
        yticklabels=["No fire", "Fire"],
        xlabel="Predicted",
        ylabel="Scenario ground truth",
        title=f"Held-out runs: {winner}",
    )
    fig.savefig(output / "overview.png", dpi=150)
    plt.close(fig)
