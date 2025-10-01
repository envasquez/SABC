"""YAML file loading utilities."""

from typing import Any, Dict

import yaml

from scripts.common import setup_logging

logger = setup_logging()


def load_yaml_data(filepath: str) -> Dict[str, Any]:
    """Load and parse YAML data from a file.

    Args:
        filepath: Path to the YAML file

    Returns:
        Dictionary containing the parsed YAML data

    Raises:
        FileNotFoundError: If the file does not exist
        yaml.YAMLError: If the YAML is invalid
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data
    except FileNotFoundError:
        logger.error(f"File not found: {filepath}")
        raise
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML file: {e}")
        raise
