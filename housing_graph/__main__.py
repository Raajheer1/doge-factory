"""Import an explicit fixture into the configured HydraDB graph."""

import argparse
import json
from pathlib import Path

from .graph import HousingGraph


def main():
    parser = argparse.ArgumentParser(description="Import a validated housing-policy graph fixture")
    parser.add_argument(
        "fixture", nargs="?", type=Path,
        default=Path(__file__).resolve().parent.parent / "fixtures" / "fictional_housing.json",
        help="JSON fixture (defaults to the fictional example)",
    )
    args = parser.parse_args()
    fixture = json.loads(args.fixture.read_text())
    graph = HousingGraph.from_env()
    graph.import_fixture(fixture)
    print(f"Imported {len(fixture['nodes'])} nodes and {len(fixture['relationships'])} relationships "
          f"into {graph.database}/{graph.collection}")


if __name__ == "__main__":
    main()
