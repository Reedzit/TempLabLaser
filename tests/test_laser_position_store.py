import json
import tempfile
import unittest
from pathlib import Path

from src.hexapod.laserPositionStore import load_laser_position, save_laser_position


class LaserPositionStoreTests(unittest.TestCase):
    def test_round_trips_laser_position(self):
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "hexapod_state.json"

            saved_position = save_laser_position((1, 2.5, -3), state_path)

            self.assertEqual((1.0, 2.5, -3.0), saved_position)
            self.assertEqual(saved_position, load_laser_position(state_path))
            self.assertEqual(
                {"version": 1, "laser_position": [1.0, 2.5, -3.0]},
                json.loads(state_path.read_text(encoding="utf-8")),
            )

    def test_missing_file_returns_none(self):
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "missing.json"

            self.assertIsNone(load_laser_position(state_path))

    def test_invalid_file_returns_none(self):
        invalid_states = (
            "not json",
            '{"version": 2, "laser_position": [1, 2, 3]}',
            '{"version": 1, "laser_position": [1, 2]}',
            '{"version": 1, "laser_position": [1, "two", 3]}',
        )

        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "hexapod_state.json"
            for state in invalid_states:
                with self.subTest(state=state):
                    state_path.write_text(state, encoding="utf-8")
                    self.assertIsNone(load_laser_position(state_path))

    def test_rejects_invalid_position_before_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "hexapod_state.json"

            with self.assertRaises(ValueError):
                save_laser_position((1, float("nan"), 3), state_path)

            self.assertFalse(state_path.exists())


if __name__ == "__main__":
    unittest.main()
