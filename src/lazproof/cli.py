from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .geometry import read_selection
from .verify import VerificationInputError, verify_subset


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="lazproof", description=__doc__)
    root.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = root.add_subparsers(dest="command", required=True)
    verify = commands.add_parser("verify", help="verify an exact ordered subset")
    verify.add_argument("source")
    verify.add_argument("result")
    verify.add_argument(
        "--inside", metavar="MASK", help="WKT or vector dataset selecting source points"
    )
    verify.add_argument("--layer", help="vector layer used with --inside")
    verify.add_argument("--report", type=Path, help="write the JSON report to this path")
    verify.add_argument("--chunk-size", type=int, default=250_000)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        geometry = read_selection(args.inside, args.layer) if args.inside else None
        report = verify_subset(args.source, args.result, geometry, chunk_size=args.chunk_size)
        payload = json.dumps(report.to_dict(), indent=2, ensure_ascii=False)
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            temporary = args.report.with_suffix(args.report.suffix + ".tmp")
            temporary.write_text(payload + "\n", encoding="utf-8")
            temporary.replace(args.report)
        print(payload)
        return 0 if report.verified else 1
    except (OSError, ValueError, VerificationInputError) as exc:
        print(f"lazproof: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
