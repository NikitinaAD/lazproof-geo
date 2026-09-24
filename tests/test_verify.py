import json

import laspy
import numpy as np
from shapely.geometry import box, mapping

from lazproof.cli import main
from lazproof.verify import verify_subset


def write_cloud(path, indices=range(10), mutate=None):
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


def test_exact_spatial_subset(tmp_path):
    source = tmp_path / "source.laz"
    result = tmp_path / "result.laz"
    write_cloud(source)
    write_cloud(result, range(2, 7))
    report = verify_subset(source, result, box(1.5, 1.5, 6.5, 6.5), chunk_size=2)
    assert report.verified
    assert report.expected_points == 5
    assert report.result_points == 5


def test_reordering_and_mutation_are_rejected(tmp_path):
    source = tmp_path / "source.las"
    reordered = tmp_path / "reordered.las"
    changed = tmp_path / "changed.las"
    write_cloud(source)
    write_cloud(reordered, reversed(range(10)))
    write_cloud(changed, mutate=5)
    assert not verify_subset(source, reordered).verified
    assert not verify_subset(source, changed).verified


def test_cli_writes_machine_readable_report(tmp_path):
    source = tmp_path / "source.laz"
    result = tmp_path / "result.laz"
    mask = tmp_path / "mask.geojson"
    report = tmp_path / "report.json"
    write_cloud(source)
    write_cloud(result, range(4))
    mask.write_text(json.dumps(mapping(box(-1, -1, 3.5, 3.5))), encoding="utf-8")
    assert main(["verify", str(source), str(result), "--inside", str(mask), "--report", str(report)]) == 0
    assert json.loads(report.read_text(encoding="utf-8"))["verified"] is True

