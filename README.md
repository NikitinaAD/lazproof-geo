# lazproof-geo

**Prove that a LAS/LAZ output is an exact, order-preserving spatial subset of its source.**

`lazproof` independently checks every point dimension, record order, point format,
LAS version, Extra Bytes schema, scales, offsets, CRS, and source immutability. It
does not crop point clouds and does not require PDAL.

## Install

```bash
python -m pip install lazproof-geo
```

## Use

```bash
lazproof verify source.laz clipped.laz \
  --inside boundary.geojson \
  --report proof.json
```

Exit code `0` means the claim was verified, `1` means a content mismatch, and `2`
means the input or invocation was invalid. Omit `--inside` to require an exact full
copy. Version 0.1 intentionally rejects waveform point formats 4/5/9/10.

## Python API

```python
from shapely.geometry import box
from lazproof import verify_subset

report = verify_subset("source.laz", "result.laz", box(0, 0, 100, 100))
assert report.verified, report.mismatches
```

The verifier reads files in bounded chunks. A SHA-256 digest is calculated for
each dimension in record order; matching summary statistics are not treated as
proof of equality.

## Development

```bash
python -m pip install -e ".[test]"
pytest
```

Copyright 2026 Alena Nikitina. Licensed under the Apache License 2.0.

