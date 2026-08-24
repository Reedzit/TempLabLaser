import json
import math
import os
from pathlib import Path


STATE_VERSION = 1


def get_state_path():
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        data_directory = Path(local_app_data) / "TempLabLaser"
    else:
        data_directory = Path.home() / ".templablaser"
    return data_directory / "hexapod_state.json"


def _normalize_position(position):
    if not isinstance(position, (list, tuple)) or len(position) != 3:
        raise ValueError("Laser position must contain exactly three coordinates.")

    coordinates = []
    for coordinate in position:
        if isinstance(coordinate, bool) or not isinstance(coordinate, (int, float)):
            raise ValueError("Laser position coordinates must be numbers.")
        coordinate = float(coordinate)
        if not math.isfinite(coordinate):
            raise ValueError("Laser position coordinates must be finite.")
        coordinates.append(coordinate)
    return tuple(coordinates)


def load_laser_position(state_path=None):
    state_path = Path(state_path) if state_path is not None else get_state_path()
    try:
        with state_path.open("r", encoding="utf-8") as state_file:
            state = json.load(state_file)
        if state.get("version") != STATE_VERSION:
            raise ValueError("Unsupported hexapod state version.")
        return _normalize_position(state.get("laser_position"))
    except FileNotFoundError:
        return None
    except (OSError, json.JSONDecodeError, AttributeError, ValueError) as exc:
        print(f"Could not load saved hexapod laser position: {exc}")
        return None


def save_laser_position(position, state_path=None):
    position = _normalize_position(position)
    state_path = Path(state_path) if state_path is not None else get_state_path()
    state_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = state_path.with_name(f".{state_path.name}.tmp")

    try:
        with temporary_path.open("w", encoding="utf-8") as state_file:
            json.dump(
                {"version": STATE_VERSION, "laser_position": position},
                state_file,
                indent=2,
            )
            state_file.write("\n")
            state_file.flush()
            os.fsync(state_file.fileno())
        temporary_path.replace(state_path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise

    return position
