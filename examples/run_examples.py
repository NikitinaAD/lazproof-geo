"""Generate and verify all documented lazproof scenarios."""

from __future__ import annotations

import json

from make_example import OUTPUT
from make_example import main as make_example

from lazproof.geometry import read_selection
from lazproof.verify import verify_subset


def main() -> None:
    make_example()
    source = OUTPUT / "source.laz"
    mask = read_selection(str(OUTPUT / "mask.wkt"))
    empty_mask = read_selection(str(OUTPUT / "empty-mask.wkt"))
    scenarios = {
        "valid": ("valid.laz", mask, True, set()),
        "reordered": ("reordered.laz", mask, False, {"dimension_hashes_match"}),
        "mutated": ("mutated.laz", mask, False, {"dimension_hashes_match"}),
        "missing": ("missing.laz", mask, False, {"point_count_matches"}),
        "outside_mask": (
            "outside-mask.laz",
            mask,
            False,
            {"all_result_points_inside", "point_count_matches"},
        ),
        "header_mismatch": (
            "header-mismatch.laz",
            mask,
            False,
            {"header_preserved"},
        ),
        "crs_mismatch": ("crs-mismatch.laz", mask, False, {"header_preserved"}),
        "schema_mismatch": (
            "schema-mismatch.laz",
            mask,
            False,
            {"header_preserved", "dimension_hashes_match"},
        ),
        "empty": ("empty.laz", empty_mask, True, set()),
    }
    summary = []
    for name, (filename, geometry, expected, failed_checks) in scenarios.items():
        report = verify_subset(source, OUTPUT / filename, geometry, chunk_size=3)
        actual_failed = {key for key, passed in report.checks.items() if not passed}
        if report.verified is not expected or not failed_checks.issubset(actual_failed):
            raise AssertionError(
                f"{name}: expected verified={expected} and failures={sorted(failed_checks)}, "
                f"got verified={report.verified} and failures={sorted(actual_failed)}"
            )
        (OUTPUT / f"{name}.json").write_text(
            json.dumps(report.to_dict(), indent=2) + "\n",
            encoding="utf-8",
        )
        summary.append(
            {
                "scenario": name,
                "verified": report.verified,
                "expected_points": report.expected_points,
                "result_points": report.result_points,
                "failed_checks": sorted(actual_failed),
            }
        )
        print(f"{name:16} verified={str(report.verified):5} failed={sorted(actual_failed)}")
    (OUTPUT / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
