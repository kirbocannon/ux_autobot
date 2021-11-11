import time
import json
import logging
import os
import yaml
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)
logging.getLogger().setLevel(logging.DEBUG)


def load_yaml(filename: str) -> dict:
    """
    Args
      filename (str): full path for filename to open

    """
    with open(filename, "r") as stream:
        try:
            data = yaml.safe_load(stream)
        except yaml.YAMLError as e:
            logger.error(f"Can't load {filename!r}: {e}")
            return {}

    return data


def get_abs_path(reference_file: str) -> Path.parent:
    return Path(os.path.abspath(reference_file)).parent


def save_har(
    location: str,
    data: dict,
    prefix: Optional[str] = None,
    timestamp: Optional[float] = None,
) -> bool:
    har_dirname = "hars"
    timestamp = time.time() if not timestamp else timestamp
    os.makedirs(f"{location}/{har_dirname}", mode=0o777, exist_ok=True)
    filename = f"{timestamp}.json" if not prefix else f"{prefix}_{timestamp}.json"
    filepath = f"{location}/{har_dirname}/{filename}"

    with open(filepath, "w+") as f:
        json.dump(data, f)

    return dict(filename=filename)


def get_filenames(directory: str) -> Tuple[str]:
    """
    Gets filenames for a given directory
    Returns a tuple of filenames sorted by created date
    oldest -> newest

    """

    files = [
        f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))
    ]
    files.sort(key=lambda x: os.path.getmtime(f"{directory}/{x}"))

    return tuple(files)
