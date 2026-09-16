import json
import tempfile
import unittest
from pathlib import Path

from src.hexapod.laserPositionStore import (
    ZERO_BIAS,
    ZERO_POSE,
    load_laser_calibration,
    load_laser_position,
    load_rotation_pivot_bias,
    save_laser_calibration,
    save_laser_position,
    save_rotation_pivot_bias,
)


class LaserPositionStoreTests(unittest.TestCase):
    def test_round_trips_laser_position(self):
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "hexapod_state.json"

            saved_position = save_laser_position((1, 2.5, -3), state_path)

            self.assertEqual((1.0, 2.5, -3.0), saved_position)
            self.assertEqual(saved_position, load_laser_position(state_path))
            self.assertEqual(
                {
                    "version": 3,
                    "laser_position": [1.0, 2.5, -3.0],
                    "reference_pose": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                    "rotation_pivot_bias": [0.0, 0.0],
                },
                json.loads(state_path.read_text(encoding="utf-8")),
            )

    def test_round_trips_reference_pose(self):
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "hexapod_state.json"
            pose = (1, 2, 3, 0.25, -0.5, 0)

            saved = save_laser_calibration((4, 5, 6), pose, state_path)

            self.assertEqual(((4.0, 5.0, 6.0), tuple(float(v) for v in pose)), saved)
            self.assertEqual(saved, load_laser_calibration(state_path))

    def test_version_one_state_uses_zero_reference_pose(self):
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "hexapod_state.json"
            state_path.write_text(
                '{"version": 1, "laser_position": [1, 2, 3]}',
                encoding="utf-8",
            )

            self.assertEqual(((1.0, 2.0, 3.0), ZERO_POSE), load_laser_calibration(state_path))
            self.assertEqual(ZERO_BIAS, load_rotation_pivot_bias(state_path))

    def test_version_two_state_uses_zero_pivot_bias(self):
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "hexapod_state.json"
            state_path.write_text(
                '{"version": 2, "laser_position": [1, 2, 3], '
                '"reference_pose": [0, 0, 0, 0, 0, 0]}',
                encoding="utf-8",
            )

            self.assertEqual(ZERO_BIAS, load_rotation_pivot_bias(state_path))

    def test_pivot_bias_round_trips_without_changing_calibration(self):
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "hexapod_state.json"
            calibration = save_laser_calibration(
                (1, 2, 3),
                (4, 5, 6, 0, 0, 0),
                state_path,
            )

            saved_bias = save_rotation_pivot_bias((0.025, -0.04), state_path)

            self.assertEqual((0.025, -0.04), saved_bias)
            self.assertEqual(saved_bias, load_rotation_pivot_bias(state_path))
            self.assertEqual(calibration, load_laser_calibration(state_path))

    def test_pivot_bias_requires_a_laser_calibration(self):
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "hexapod_state.json"

            with self.assertRaisesRegex(ValueError, "must be calibrated"):
                save_rotation_pivot_bias((0.01, 0.02), state_path)

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
