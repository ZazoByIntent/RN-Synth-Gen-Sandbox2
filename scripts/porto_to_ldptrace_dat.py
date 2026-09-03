"""Convert the Kaggle Porto taxi file into the LDPTrace reference inputs.

Thin argparse wrapper around ``trajguard.datasets.ldptrace_dat.convert_porto``
(docs/NACRT_LDPTRACE_VALIDACIJA.md, D-V.2; docs/RUNNING.md §9.1)::

    uv run python scripts/porto_to_ldptrace_dat.py data/raw/porto/train.csv data/interim/porto \\
        [--bbox MIN_LON MIN_LAT MAX_LON MAX_LAT] [--max-trajectories N]

Writes ``porto.dat``, ``porto.xz`` and ``porto_stats.json`` under the output directory
(never under ``data/raw/``) and prints the stats as JSON.
"""

import argparse
import json
import time
from pathlib import Path

from trajguard.datasets.ldptrace_dat import PORTO_CENTRE_BBOX, convert_porto


def main() -> None:
    """Parse the command line, run the conversion, print the stats."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("csv_path", type=Path, help="Kaggle train.csv (read only)")
    parser.add_argument("out_dir", type=Path, help="output directory (not under data/raw/)")
    parser.add_argument(
        "--bbox",
        type=float,
        nargs=4,
        metavar=("MIN_LON", "MIN_LAT", "MAX_LON", "MAX_LAT"),
        default=list(PORTO_CENTRE_BBOX),
        help=f"keep only trajectories entirely inside this bbox (default {PORTO_CENTRE_BBOX})",
    )
    parser.add_argument(
        "--max-trajectories",
        type=int,
        default=None,
        help="stop after this many kept trajectories (smoke runs)",
    )
    args = parser.parse_args()
    started = time.perf_counter()
    bbox = (args.bbox[0], args.bbox[1], args.bbox[2], args.bbox[3])
    stats = convert_porto(args.csv_path, args.out_dir, bbox, args.max_trajectories)
    print(json.dumps(stats, indent=2))
    print(f"done in {time.perf_counter() - started:.1f} s -> {args.out_dir}")


if __name__ == "__main__":
    main()
