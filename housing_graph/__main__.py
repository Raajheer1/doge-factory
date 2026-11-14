"""Import the fictional fixture into the configured HydraDB graph."""

import json
from pathlib import Path

from .graph import HousingGraph


def main():
    fixture = json.loads((Path(__file__).resolve().parent.parent / "fixtures" / "fictional_housing.json").read_text())
    graph = HousingGraph.from_env()
    graph.import_fixture(fixture)
    print(f"Imported {len(fixture['nodes'])} nodes and {len(fixture['relationships'])} relationships "
          f"into {graph.database}/{graph.collection}")


if __name__ == "__main__":
    main()
