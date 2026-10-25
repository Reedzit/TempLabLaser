import datetime
import os
import tempfile
import threading
import unittest

import numpy as np
import pandas as pd

from src.measurementWorkflow import (
    create_measurement_directory,
    run_angle_sweeps,
    save_angle_sweep,
)


class FakeHexapod:
    def __init__(self):
        self.ready_for_commands = True
        self.rotations = []

    def rotateAroundLaser(self, rotation):
        self.rotations.append(tuple(rotation))
        return "Success."


class FakeInstruments:
    def __init__(self, fail_at=None):
        self.fail_at = fail_at
        self.measured_angles = []

    def measure_frequency_sweep(self, _settings, degree=None, progress_callback=None, **_options):
        self.measured_angles.append(degree)
        if degree == self.fail_at:
            raise RuntimeError("measurement failed")
        data = pd.DataFrame({
            "FrequencyIn": [1.0],
            "AmplitudeOut": [2.0],
            "Degrees of Rotation": [degree],
        })
        if progress_callback:
            progress_callback(data, 1, 1)
        return data


class MeasurementWorkflowTests(unittest.TestCase):
    def test_standard_run_and_angle_paths_match_existing_suite_convention(self):
        timestamp = datetime.datetime(2026, 9, 20, 15, 30)
        data = pd.DataFrame({"FrequencyIn": [1.0], "AmplitudeOut": [2.0]})

        with tempfile.TemporaryDirectory() as root:
            measurement_directory = create_measurement_directory(
                root, "QX001", "5.0", "0.0", timestamp=timestamp
            )
            output_path = save_angle_sweep(
                measurement_directory, -0.125, 0.075, -19.0, data
            )

            expected_directory = os.path.join(
                root,
                "QX001Date_Sep-20-2026",
                "Measurement_15-30PM_BO5.0um_Angle0.0deg",
            )
            self.assertEqual(expected_directory, measurement_directory)
            self.assertEqual(
                os.path.join(
                    expected_directory,
                    "x_-0.125_y_0.075",
                    "-19.0_degrees.csv",
                ),
                output_path,
            )
            pd.testing.assert_frame_equal(data, pd.read_csv(output_path))

    def test_angle_runner_publishes_sweeps_and_restores_orientation(self):
        hexapod = FakeHexapod()
        instruments = FakeInstruments()
        published = []
        saved = []

        frames = run_angle_sweeps(
            hexapod,
            instruments,
            settings=None,
            angles=np.array([-10.0, 10.0]),
            cancel_event=threading.Event(),
            on_sweep=lambda index, angle, data: saved.append((index, angle, data.copy())),
            on_data=lambda data: published.append(data.copy()),
        )

        self.assertEqual([-10.0, 10.0], instruments.measured_angles)
        self.assertEqual(2, len(frames))
        self.assertEqual(2, len(saved))
        self.assertEqual(2, len(published))
        self.assertEqual(
            [(0.0, 0.0, -10.0), (0.0, 0.0, 20.0), (0.0, 0.0, -10.0)],
            hexapod.rotations,
        )

    def test_angle_runner_restores_orientation_after_measurement_failure(self):
        hexapod = FakeHexapod()
        instruments = FakeInstruments(fail_at=10.0)

        with self.assertRaisesRegex(RuntimeError, "measurement failed"):
            run_angle_sweeps(
                hexapod,
                instruments,
                settings=None,
                angles=np.array([-10.0, 10.0]),
            )

        self.assertEqual(
            [(0.0, 0.0, -10.0), (0.0, 0.0, 20.0), (0.0, 0.0, -10.0)],
            hexapod.rotations,
        )


if __name__ == "__main__":
    unittest.main()
