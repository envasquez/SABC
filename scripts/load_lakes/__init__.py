"""Lake and ramp data loading from YAML files."""

from scripts.load_lakes.data_loader import load_lakes_and_ramps
from scripts.load_lakes.lake_inserter import insert_lake
from scripts.load_lakes.ramp_inserter import insert_ramps
from scripts.load_lakes.yaml_loader import load_yaml_data

__all__ = [
    "load_lakes_and_ramps",
    "insert_lake",
    "insert_ramps",
    "load_yaml_data",
]
