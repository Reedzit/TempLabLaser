import threading
import unittest
import queue

import numpy as np
import pandas as pd

from src.gui_tabs.rasteringTab import (
    RasteringTab,
    calculate_average_amplitude_noise,
    generate_centered_angles,
    generate_scan_positions,
)
from src.instrumentManager import InstrumentInitialize
from src.measurementTiming import angle_workflow_seconds, heatmap_seconds


class ImmediateParent:
    def after(self, _delay, callback):
        callback()


class FakeHexapod:
    def __init__(self):
        self.ready_for_commands = True
        self.translations = []
        self.rotations = []

    def translate(self, movement):
        self.translations.append(tuple(movement))
        return "Success."

    def rotateAroundLaser(self, rotation):
        self.rotations.append(tuple(rotation))
        return "Success."


class FakeInstruments:
    def __init__(self):
        self.degrees = []

    def measure_frequency_sweep(self, _settings, degree=None, **_options):
        self.degrees.append(degree)
        return pd.DataFrame({
            "Time": ["first", "second", "third", "fourth"],
            "index": [0, 0, 1, 1],
            "FrequencyIn": [10.0, 10.0, 20.0, 20.0],
            "AmplitudeOut": [1.0, 3.0, 2.0, 6.0],
            "PhaseOut": [0.0, 0.0, 0.0, 0.0],
            "RealOut": [0.0, 0.0, 0.0, 0.0],
            "ImagOut": [0.0, 0.0, 0.0, 0.0],
            "Convergence": [False, False, False, False],
            "Degrees of Rotation": [degree] * 4,
        })


class DiffusivityRasterTests(unittest.TestCase):
    def test_measurement_time_formulas(self):
        sweep = 5 * 2
        rotations = angle_workflow_seconds(3, sweep)
        self.assertEqual(36.0, rotations)
        self.assertEqual(380.0, heatmap_seconds(10, rotations))

    def test_scan_positions_do_not_overshoot_end(self):
        positions = generate_scan_positions(-1.0, 1.0, 0.6)
        np.testing.assert_allclose([-1.0, -0.4, 0.2, 0.8], positions)

    def test_angles_are_centered_and_single_step_is_zero(self):
        np.testing.assert_allclose([-10.0, 0.0, 10.0], generate_centered_angles(20.0, 3))
        np.testing.assert_allclose([0.0], generate_centered_angles(20.0, 1))

    def test_noise_averages_each_angle_frequency_standard_deviation(self):
        data = pd.DataFrame({
            "Degrees of Rotation": [0, 0, 0, 0, 10, 10, 10, 10],
            "FrequencyIn": [1, 1, 2, 2, 1, 1, 2, 2],
            "AmplitudeOut": [1, 3, 2, 6, 4, 4, 0, 8],
        })
        self.assertAlmostEqual(1.75, calculate_average_amplitude_noise(data))

    def test_noise_ignores_incomplete_frequency_groups(self):
        data = pd.DataFrame({
            "Degrees of Rotation": [0, 0, 10],
            "FrequencyIn": [1, 1, 2],
            "AmplitudeOut": [1, 3, 100],
        })
        self.assertAlmostEqual(1.0, calculate_average_amplitude_noise(data))

    def test_non_finite_scan_and_angle_values_are_rejected(self):
        with self.assertRaises(ValueError):
            generate_scan_positions(0.0, np.nan, 1.0)
        with self.assertRaises(ValueError):
            generate_centered_angles(np.inf, 3)

    def test_raster_runs_each_angle_and_restores_cell_orientation(self):
        raster = RasteringTab.__new__(RasteringTab)
        raster.parent = ImmediateParent()
        raster.instruments = FakeInstruments()
        raster.cancel_event = threading.Event()
        raster.raw_measurements = []
        raster.cell_summaries = []
        raster.scan_running = True
        raster._update_heatmap = lambda: None
        raster._update_progress = lambda _progress, _message: None
        completed = []
        raster._scan_complete = completed.append
        hexapod = FakeHexapod()
        raster.get_hexapod = lambda: hexapod

        raster._run_raster_scan({
            "x_start": 0.0,
            "x_end": 0.0,
            "y_start": 0.0,
            "y_end": 0.0,
            "step_size": 1.0,
            "dwell_time": 0.0,
            "angles": np.array([-10.0, 10.0]),
            "laser_settings": ((10, 20), (1, 1), (0, 0), 0, 2, 5, "linspace"),
            "wait_for_convergence": False,
            "return_to_origin": False,
        })

        self.assertEqual([-10.0, 10.0], raster.instruments.degrees)
        self.assertEqual(
            [(0.0, 0.0, -10.0), (0.0, 0.0, 20.0), (0.0, 0.0, -10.0)],
            hexapod.rotations,
        )
        self.assertAlmostEqual(1.5, raster.scan_data[0, 0])
        self.assertEqual("Scan complete", completed[0])


class FrequencySweepTests(unittest.TestCase):
    def test_measurement_ranges_support_linear_and_log_spacing(self):
        linear = ((1, 3), (2, 4), (0, 2), 0, 3, 5, "linspace")
        logarithmic = ((1, 100), (2, 2), (0, 0), 0, 3, 5, "logspace")
        self.assertEqual([1.0, 2.0, 3.0], InstrumentInitialize.build_measurement_ranges(linear)[0])
        np.testing.assert_allclose(
            [1.0, 10.0, 100.0],
            InstrumentInitialize.build_measurement_ranges(logarithmic)[0],
        )

    def test_synchronous_sweep_returns_samples_and_honors_cancellation(self):
        instruments = InstrumentInitialize.__new__(InstrumentInitialize)
        configured = []
        instruments.update_configuration = lambda **values: configured.append(values)
        instruments.take_measurement = lambda: (2.0, 3.0, 4.0, 5.0)
        cancel_event = threading.Event()

        def cancel_after_first_frequency(_data, completed, _total):
            if completed == 1:
                cancel_event.set()

        settings = ((1, 3), (2, 2), (0, 0), 0, 3, 5, "linspace")
        data = instruments.measure_frequency_sweep(
            settings,
            cancel_event=cancel_event,
            progress_callback=cancel_after_first_frequency,
        )

        self.assertEqual(2, len(data))
        self.assertEqual(1, len(configured))
        self.assertEqual(1.0, data.iloc[0]["FrequencyIn"])

    def test_standalone_stop_is_reported_as_cancelled(self):
        instruments = InstrumentInitialize.__new__(InstrumentInitialize)
        instruments.workflow_lock = threading.Lock()
        instruments.q = queue.Queue()
        instruments.q.put("stop")
        instruments.automationQueue = queue.LifoQueue()
        instruments.update_configuration = lambda **_values: None
        instruments.take_measurement = lambda: (2.0, 3.0, 4.0, 5.0)
        settings = ((1, 3), (2, 2), (0, 0), 0, 3, 5, "linspace")

        data = instruments.automatic_measuring(settings, None, False)

        self.assertTrue(data.empty)
        self.assertEqual("cancelled", instruments.automation_status)


if __name__ == "__main__":
    unittest.main()
