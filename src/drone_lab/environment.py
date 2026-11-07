"""Configurable teaching environments; presets are assumptions, not calibrated climates."""

from dataclasses import asdict, dataclass

import numpy as np

PRESETS = {
    "forest": {"temperature_offset_c": 0.0, "humidity_offset_pct": 0.0},
    "meadow": {"temperature_offset_c": 3.0, "humidity_offset_pct": -8.0},
    "desert": {"temperature_offset_c": 12.0, "humidity_offset_pct": -25.0},
}


@dataclass(frozen=True)
class Environment:
    preset: str = "forest"
    width_m: float = 220
    sensor_count: int = 12
    vegetation: int = 70

    def __post_init__(self):
        if self.preset not in PRESETS:
            raise ValueError("Choose forest, meadow or desert")
        if not np.isfinite(self.width_m) or not 150 <= self.width_m <= 600:
            raise ValueError("Field width must be 150..600 metres")
        if not 6 <= self.sensor_count <= 60 or not 0 <= self.vegetation <= 100:
            raise ValueError("Use 6..60 sensors and vegetation 0..100")

    @property
    def height_m(self) -> float:
        return self.width_m * 160 / 220

    def positions(self) -> np.ndarray:
        columns = int(np.ceil(np.sqrt(self.sensor_count * 4 / 3)))
        rows = int(np.ceil(self.sensor_count / columns))
        xs = np.linspace(20, self.width_m - 20, columns)
        ys = np.linspace(20, self.height_m - 20, rows)
        return np.array([(xs[i % columns], ys[i // columns]) for i in range(self.sensor_count)])

    def paths(self, steps: int, drones: int) -> list[np.ndarray]:
        """Equal-speed closed tour, with drones spaced around the same circuit."""
        positions = self.positions()
        columns = int(np.ceil(np.sqrt(self.sensor_count * 4 / 3)))
        order = []
        for row, start in enumerate(range(0, self.sensor_count, columns)):
            indices = list(range(start, min(start + columns, self.sensor_count)))
            order.extend(indices if row % 2 == 0 else indices[::-1])
        nodes = positions[order + [order[0]]]
        distance = np.r_[0, np.cumsum(np.linalg.norm(np.diff(nodes, axis=0), axis=1))]
        base = np.column_stack(
            [
                np.interp(np.linspace(0, distance[-1], steps), distance, nodes[:, axis])
                for axis in (0, 1)
            ]
        )
        paths = []
        for drone in range(drones):
            shifted = np.roll(base[:-1], -(drone * (steps - 1) // drones), axis=0)
            paths.append(np.vstack([shifted, shifted[0]]))
        return paths

    def to_dict(self) -> dict:
        return asdict(self) | {"height_m": self.height_m, **PRESETS[self.preset]}
