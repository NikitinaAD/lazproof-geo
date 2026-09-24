"""Create the synthetic LAZ files used in the README."""

from pathlib import Path

import laspy
import numpy as np

ROOT = Path(__file__).parent


def write_cloud(path: Path, indices, *, mutate: int | None = None) -> None:
    indices = list(indices)
    header = laspy.LasHeader(point_format=3, version="1.2")
    header.scales = np.array([0.01, 0.01, 0.01])
    cloud = laspy.LasData(header)
    cloud.x = np.asarray(indices, dtype=float)
    cloud.y = np.asarray(indices, dtype=float)
    cloud.z = np.asarray(indices, dtype=float) * 2
    cloud.intensity = np.asarray(indices, dtype=np.uint16) * 7
    if mutate is not None:
        cloud.intensity[mutate] += 1
    cloud.write(path)


def main() -> None:
    write_cloud(ROOT / "source.laz", range(10))
    write_cloud(ROOT / "subset.laz", range(2, 7))
    write_cloud(ROOT / "reordered.laz", reversed(range(2, 7)))
    write_cloud(ROOT / "mutated.laz", range(2, 7), mutate=2)
    (ROOT / "mask.wkt").write_text(
        "POLYGON ((1.5 1.5, 6.5 1.5, 6.5 6.5, 1.5 6.5, 1.5 1.5))\n",
        encoding="utf-8",
    )
    print(f"Wrote synthetic example files to {ROOT}")


if __name__ == "__main__":
    main()
