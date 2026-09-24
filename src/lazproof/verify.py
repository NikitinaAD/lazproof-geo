from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from pathlib import Path

import laspy
import numpy as np
from shapely import intersects_xy
from shapely.geometry.base import BaseGeometry

UNSUPPORTED_WAVEFORM_FORMATS = {4, 5, 9, 10}


class VerificationInputError(ValueError):
    """The requested verification cannot be performed safely."""


@dataclass(frozen=True)
class StreamDigest:
    points: int
    records_sha256: str
    outside_geometry: int = 0


@dataclass
class VerificationReport:
    verified: bool
    source: str
    result: str
    expected_points: int
    result_points: int
    source_points: int
    dimensions: list[str]
    source_sha256: str
    result_sha256: str
    checks: dict[str, bool]
    mismatches: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _file_sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _crs_text(header: laspy.LasHeader) -> str | None:
    crs = header.parse_crs()
    return crs.to_wkt() if crs is not None else None


def _schema(header: laspy.LasHeader) -> list[tuple[str, str]]:
    schema = []
    for name in header.point_format.dimension_names:
        info = header.point_format.dimension_by_name(name)
        schema.append((name, str(info.dtype)))
    return schema


def _header_snapshot(header: laspy.LasHeader) -> dict:
    return {
        "version": str(header.version),
        "point_format": int(header.point_format.id),
        "schema": _schema(header),
        "scales": [float(v).hex() for v in header.scales],
        "offsets": [float(v).hex() for v in header.offsets],
        "crs": _crs_text(header),
    }


def _stream_digest(
    path: Path,
    geometry: BaseGeometry | None,
    *,
    require_inside: bool,
    chunk_size: int,
) -> StreamDigest:
    digest = hashlib.sha256()
    point_count = 0
    outside_count = 0
    with laspy.open(path) as reader:
        for chunk in reader.chunk_iterator(chunk_size):
            if geometry is None:
                records = chunk
            else:
                mask = intersects_xy(geometry, np.asarray(chunk.x), np.asarray(chunk.y))
                if require_inside:
                    outside_count += int(np.count_nonzero(~mask))
                    records = chunk
                else:
                    records = chunk[mask]
            point_count += len(records)
            digest.update(np.ascontiguousarray(records.array).tobytes())
    return StreamDigest(
        points=point_count,
        records_sha256=digest.hexdigest(),
        outside_geometry=outside_count,
    )


def verify_subset(
    source: str | Path,
    result: str | Path,
    geometry: BaseGeometry | None = None,
    *,
    chunk_size: int = 250_000,
) -> VerificationReport:
    """Verify that *result* is the exact ordered source subset selected by geometry.

    Raw structured LAS point records are hashed in order after spatial selection.
    When geometry is omitted, the result must contain every source point without
    modification.
    """
    source_path = Path(source).resolve()
    result_path = Path(result).resolve()
    if source_path == result_path:
        raise VerificationInputError("Source and result must be different files")
    if not source_path.is_file() or not result_path.is_file():
        raise VerificationInputError("Source and result must both exist")
    if chunk_size <= 0:
        raise VerificationInputError("chunk_size must be positive")
    if geometry is not None and (geometry.is_empty or not geometry.is_valid):
        raise VerificationInputError("Selection geometry must be non-empty and valid")
    if geometry is not None and geometry.geom_type not in {"Polygon", "MultiPolygon"}:
        raise VerificationInputError("Selection geometry must be Polygon or MultiPolygon")

    source_before = _file_sha256(source_path)
    with laspy.open(source_path) as source_reader, laspy.open(result_path) as result_reader:
        source_header = source_reader.header
        result_header = result_reader.header
        if source_header.point_format.id in UNSUPPORTED_WAVEFORM_FORMATS:
            raise VerificationInputError(
                "Waveform point formats 4, 5, 9 and 10 are not supported in v0.1"
            )
        if result_header.point_format.id in UNSUPPORTED_WAVEFORM_FORMATS:
            raise VerificationInputError(
                "Waveform point formats 4, 5, 9 and 10 are not supported in v0.1"
            )
        source_points = int(source_header.point_count)
        source_meta = _header_snapshot(source_header)
        result_meta = _header_snapshot(result_header)

    expected = _stream_digest(source_path, geometry, require_inside=False, chunk_size=chunk_size)
    actual = _stream_digest(
        result_path, geometry, require_inside=geometry is not None, chunk_size=chunk_size
    )
    source_after = _file_sha256(source_path)
    result_hash = _file_sha256(result_path)

    checks = {
        "source_unchanged": source_before == source_after,
        "header_preserved": source_meta == result_meta,
        "point_count_matches": expected.points == actual.points,
        "dimension_hashes_match": expected.records_sha256 == actual.records_sha256,
        "all_result_points_inside": actual.outside_geometry == 0,
    }
    labels = {
        "source_unchanged": "source file changed during verification",
        "header_preserved": "LAS version, point format, schema, scales, offsets or CRS differ",
        "point_count_matches": "result point count does not match the selected source subset",
        "dimension_hashes_match": "one or more point dimensions differ or point order changed",
        "all_result_points_inside": "result contains points outside the selection geometry",
    }
    mismatches = [labels[name] for name, passed in checks.items() if not passed]
    return VerificationReport(
        verified=all(checks.values()),
        source=str(source_path),
        result=str(result_path),
        expected_points=expected.points,
        result_points=actual.points,
        source_points=source_points,
        dimensions=[name for name, _ in source_meta["schema"]],
        source_sha256=source_after,
        result_sha256=result_hash,
        checks=checks,
        mismatches=mismatches,
    )
