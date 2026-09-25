import json

import laspy
import numpy as np
import pytest
from pyproj import CRS
from shapely.geometry import box, mapping

from lazproof.cli import main
from lazproof.verify import verify_subset


def write_cloud(
    path,
    indices=range(10),
    mutate=None,
    scales=None,
    crs=None,
    extra_dimension=False,
):
    indices = list(indices)
    header = laspy.LasHeader(point_format=3, version="1.2")
    header.scales = np.asarray(scales or [0.01, 0.01, 0.01])
    if crs is not None:
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


def test_exact_spatial_subset(tmp_path):
    source = tmp_path / "source.laz"
    result = tmp_path / "result.laz"
    write_cloud(source)
    write_cloud(result, range(2, 7))
    report = verify_subset(source, result, box(1.5, 1.5, 6.5, 6.5), chunk_size=2)
    assert report.verified
    assert report.expected_points == 5
    assert report.result_points == 5


@pytest.mark.parametrize("chunk_size", [1, 3, 50])
def test_chunk_boundaries_do_not_change_the_proof(tmp_path, chunk_size):
    source = tmp_path / "source.laz"
    result = tmp_path / "result.laz"
    write_cloud(source)
    write_cloud(result, range(2, 7))
    assert verify_subset(
        source,
        result,
        box(1.5, 1.5, 6.5, 6.5),
        chunk_size=chunk_size,
    ).verified


def test_empty_subset_is_valid(tmp_path):
    source = tmp_path / "source.laz"
    result = tmp_path / "empty.laz"
    write_cloud(source)
    write_cloud(result, [])
    report = verify_subset(source, result, box(100, 100, 110, 110), chunk_size=2)
    assert report.verified
    assert report.expected_points == report.result_points == 0


def test_reordering_and_mutation_are_rejected(tmp_path):
    source = tmp_path / "source.las"
    reordered = tmp_path / "reordered.las"
    changed = tmp_path / "changed.las"
    write_cloud(source)
    write_cloud(reordered, reversed(range(10)))
    write_cloud(changed, mutate=5)
    assert not verify_subset(source, reordered).verified
    assert not verify_subset(source, changed).verified


def test_header_mismatch_and_point_outside_mask_are_reported(tmp_path):
    source = tmp_path / "source.laz"
    different_header = tmp_path / "different-header.laz"
    outside = tmp_path / "outside.laz"
    write_cloud(source)
    write_cloud(different_header, range(2, 7), scales=[0.1, 0.1, 0.1])
    write_cloud(outside, range(2, 8))
    geometry = box(1.5, 1.5, 6.5, 6.5)
    header_report = verify_subset(source, different_header, geometry)
    outside_report = verify_subset(source, outside, geometry)
    assert not header_report.checks["header_preserved"]
    assert not outside_report.checks["all_result_points_inside"]
    assert not outside_report.checks["point_count_matches"]


def test_crs_and_schema_mismatches_are_reported(tmp_path):
    source = tmp_path / "source.laz"
    different_crs = tmp_path / "different-crs.laz"
    different_schema = tmp_path / "different-schema.laz"
    write_cloud(source, crs=32637)
    write_cloud(different_crs, crs=32636)
    write_cloud(different_schema, crs=32637, extra_dimension=True)

    crs_report = verify_subset(source, different_crs)
    schema_report = verify_subset(source, different_schema)

    assert not crs_report.checks["header_preserved"]
    assert not schema_report.checks["header_preserved"]
    assert not schema_report.checks["dimension_hashes_match"]


def test_invalid_invocation_is_rejected(tmp_path):
    source = tmp_path / "source.las"
    result = tmp_path / "result.las"
    write_cloud(source)
    write_cloud(result)
    with pytest.raises(ValueError, match="different files"):
        verify_subset(source, source)
    with pytest.raises(ValueError, match="positive"):
        verify_subset(source, result, chunk_size=0)


def test_cli_writes_machine_readable_report(tmp_path):
    source = tmp_path / "source.laz"
    result = tmp_path / "result.laz"
    mask = tmp_path / "mask.geojson"
    report = tmp_path / "report.json"
    write_cloud(source)
    write_cloud(result, range(4))
    mask.write_text(json.dumps(mapping(box(-1, -1, 3.5, 3.5))), encoding="utf-8")
    assert (
        main(["verify", str(source), str(result), "--inside", str(mask), "--report", str(report)])
        == 0
    )
    assert json.loads(report.read_text(encoding="utf-8"))["verified"] is True
