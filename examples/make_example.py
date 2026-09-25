"""Create the complete synthetic verification suite used in the README."""

from pathlib import Path

import laspy
import numpy as np
from pyproj import CRS

ROOT = Path(__file__).parent
OUTPUT = ROOT / "generated"


def write_cloud(
    path: Path,
    indices,
    *,
    mutate: int | None = None,
    scales=(0.01, 0.01, 0.01),
    crs: int = 32637,
    extra_dimension: bool = False,
) -> None:
    indices = list(indices)
    header = laspy.LasHeader(point_format=3, version="1.2")
    header.scales = np.asarray(scales, dtype=float)
    header.add_crs(CRS.from_epsg(crs))
    if extra_dimension:
        header.add_extra_dim(laspy.ExtraBytesParams(name="quality", type=np.uint8))
    cloud = laspy.LasData(header)
    cloud.x = np.asarray(indices, dtype=float)
    cloud.y = np.asarray(indices, dtype=float)
    cloud.z = np.asarray(indices, dtype=float) * 2
    cloud.intensity = np.asarray(indices, dtype=np.uint16) * 7
    if extra_dimension:
        cloud.quality = np.asarray(indices, dtype=np.uint8)
    if mutate is not None:
        cloud.intensity[mutate] += 1
    cloud.write(path)


def main() -> None:
    OUTPUT.mkdir(exist_ok=True)
    write_cloud(OUTPUT / "source.laz", range(10))
    write_cloud(OUTPUT / "valid.laz", range(2, 7))
    write_cloud(OUTPUT / "reordered.laz", reversed(range(2, 7)))
    write_cloud(OUTPUT / "mutated.laz", range(2, 7), mutate=2)
    write_cloud(OUTPUT / "missing.laz", range(2, 6))
    write_cloud(OUTPUT / "outside-mask.laz", range(2, 8))
    write_cloud(OUTPUT / "header-mismatch.laz", range(2, 7), scales=(0.1, 0.1, 0.1))
    write_cloud(OUTPUT / "crs-mismatch.laz", range(2, 7), crs=32636)
    write_cloud(OUTPUT / "schema-mismatch.laz", range(2, 7), extra_dimension=True)
    write_cloud(OUTPUT / "empty.laz", [])
    (OUTPUT / "mask.wkt").write_text(
        "POLYGON ((1.5 1.5, 6.5 1.5, 6.5 6.5, 1.5 6.5, 1.5 1.5))\n",
        encoding="utf-8",
    )
    (OUTPUT / "empty-mask.wkt").write_text(
        "POLYGON ((100 100, 110 100, 110 110, 100 110, 100 100))\n",
        encoding="utf-8",
    )
    print(f"Wrote synthetic example files to {OUTPUT}")


if __name__ == "__main__":
    main()
