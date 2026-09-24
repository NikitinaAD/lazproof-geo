from __future__ import annotations

import json
from pathlib import Path

import fiona
from shapely import from_wkt
from shapely.geometry import shape
from shapely.ops import unary_union


def read_selection(value: str, layer: str | None = None):
    """Read a Polygon/MultiPolygon from WKT, GeoJSON, or any Fiona data source."""
    if value.lstrip().upper().startswith(("POLYGON", "MULTIPOLYGON")):
        geometry = from_wkt(value)
        candidate = None
    else:
        candidate = Path(value)
    if candidate is not None and not candidate.exists():
        raise ValueError(f"Selection dataset does not exist: {candidate}")
    if candidate is None:
        pass
    elif candidate.suffix.lower() == ".wkt":
        geometry = from_wkt(candidate.read_text(encoding="utf-8"))
    elif candidate.suffix.lower() in {".json", ".geojson"}:
        payload = json.loads(candidate.read_text(encoding="utf-8"))
        if payload.get("type") == "FeatureCollection":
            geometry = unary_union([shape(feature["geometry"]) for feature in payload["features"]])
        elif payload.get("type") == "Feature":
            geometry = shape(payload["geometry"])
        else:
            geometry = shape(payload)
    else:
        with fiona.open(candidate, layer=layer) as collection:
            geometry = unary_union([shape(feature["geometry"]) for feature in collection])
    if geometry.is_empty or not geometry.is_valid:
        raise ValueError("Selection geometry must be non-empty and valid")
    if geometry.geom_type not in {"Polygon", "MultiPolygon"}:
        raise ValueError("Selection geometry must be Polygon or MultiPolygon")
    return geometry
