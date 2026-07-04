"""CLI helper building OSM road networks from a YAML region config.

Usage: python -m trajguard.maps.build config/maps.yaml [--region beijing ...] [--out maps]
"""

import argparse
from pathlib import Path

import yaml

from trajguard.maps.osm import OSMMapSource


def build_from_config(config_path: Path, regions: list[str] | None, out_dir: Path) -> None:
    """Build and persist every requested region entry from the config file."""
    entries = yaml.safe_load(config_path.read_text())["maps"]
    selected = regions or [r for r in entries if not entries[r].get("fixture", False)]
    for region in selected:
        entry = entries[region]
        source = OSMMapSource(
            region=region,
            bbox=tuple(entry["bbox"]),
            crs=entry["crs"],
            out_dir=out_dir,
            network_type=entry.get("network_type", "drive"),
        )
        net = source.build()
        print(f"{region}: {len(net.nodes)} nodes, {len(net.edges)} edges -> {source.out_dir}")


def main() -> None:
    """Parse CLI arguments and run the builds."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path, help="YAML file with a top-level 'maps:' mapping")
    parser.add_argument(
        "--region", nargs="*", default=None, help="regions to build (default: all non-fixture)"
    )
    parser.add_argument("--out", type=Path, default=Path("maps"), help="output root directory")
    args = parser.parse_args()
    build_from_config(args.config, args.region, args.out)


if __name__ == "__main__":
    main()
