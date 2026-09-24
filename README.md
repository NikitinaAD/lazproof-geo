# lazproof-geo

[![CI](https://github.com/NikitinaAD/lazproof-geo/actions/workflows/ci.yml/badge.svg)](https://github.com/NikitinaAD/lazproof-geo/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/lazproof-geo.svg)](https://pypi.org/project/lazproof-geo/)
[![Python](https://img.shields.io/pypi/pyversions/lazproof-geo.svg)](https://pypi.org/project/lazproof-geo/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

**Prove that a LAS/LAZ output is an exact, order-preserving spatial subset of its source.**

Point counts and bounding boxes are not enough to catch reordered records, changed
attributes, a different Extra Bytes schema, or a subtly modified header.
`lazproof` independently streams both files and hashes complete structured point
records in order, without cropping the source and without requiring PDAL.

![Valid, reordered, and mutated outcomes](https://raw.githubusercontent.com/NikitinaAD/lazproof-geo/main/docs/outcomes.svg)

## Quick start

```bash
python -m pip install lazproof-geo
lazproof verify source.laz result.laz \
  --inside boundary.geojson \
  --report proof.json
```

Exit codes are stable:

- `0`: every requested check passed;
- `1`: verification completed and found a mismatch;
- `2`: the files, geometry, or invocation were invalid.

## Reproducible example

Generate four tiny synthetic LAZ files and a WKT mask:

```bash
python examples/make_example.py
lazproof verify examples/source.laz examples/subset.laz \
  --inside examples/mask.wkt --report examples/valid.json
lazproof verify examples/source.laz examples/reordered.laz \
  --inside examples/mask.wkt --report examples/reordered.json
lazproof verify examples/source.laz examples/mutated.laz \
  --inside examples/mask.wkt --report examples/mutated.json
```

The first command exits `0`. The next two exit `1`: one changes record order and
the other changes a single intensity value. A report contains explicit checks:

```json
{
  "verified": false,
  "expected_points": 5,
  "result_points": 5,
  "checks": {
    "source_unchanged": true,
    "header_preserved": true,
    "point_count_matches": true,
    "dimension_hashes_match": false,
    "all_result_points_inside": true
  }
}
```

## Python API

```python
from shapely.geometry import box
from lazproof import VerificationReport, verify_subset

report: VerificationReport = verify_subset(
    "source.laz",
    "result.laz",
    box(0, 0, 100, 100),
)
assert report.verified, report.mismatches
```

`verify_subset(source, result, geometry=None, *, chunk_size=250_000)` reads data in
bounded chunks. With no geometry, the result must be an exact full copy.

## What is proved

- LAS version, point format, dimension schema, scales, offsets, and CRS match.
- The result contains exactly the source records selected by the polygon.
- Every raw point dimension matches in the original record order.
- Every result point lies inside the selection geometry.
- The source file hash is unchanged during verification.

## What is not proved

- The source data is correct, authentic, or appropriate for a particular use.
- The CRS describes the real-world location correctly.
- A non-spatial filter was applied as intended.
- The source remained unchanged before or after the verification run.
- Waveform point formats 4, 5, 9, and 10 are supported; version 0.1 rejects them.

Selection geometry may be WKT, `.wkt`, GeoJSON, or a Fiona-supported vector layer.
Run `lazproof --help` for all options.

## Development

```bash
python -m pip install -e ".[test]"
python -m ruff check .
python -m ruff format --check .
python -m pytest
```

Copyright 2026 Alena Nikitina. Licensed under the [Apache License 2.0](https://github.com/NikitinaAD/lazproof-geo/blob/main/LICENSE).
