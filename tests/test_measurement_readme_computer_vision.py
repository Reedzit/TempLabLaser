import os
import tempfile
import unittest

from src.gui_tabs.automationLaserTab import READMEGenerator


class FakeVariable:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value


class FakeCameraTab:
    def collect_measurement_vision(self):
        return {
            "red": {
                "found": True,
                "center": (10.25, 20.5),
                "axes": (4.0, 9.0),
                "angle": 30.0,
                "axes_microns": ((0.092, 0.136), (0.207, 0.306)),
                "equivalent_diameter_microns": (0.138, 0.204),
            },
            "green": {
                "found": True,
                "center": (30.0, 40.0),
                "axes": (6.0, 8.0),
                "angle": 45.0,
            },
            "distance_px": 28.5,
            "distance_microns": (0.6555, 0.969),
        }


class MissingFrameCameraTab:
    def collect_measurement_vision(self):
        return None


class FailingCameraTab:
    def collect_measurement_vision(self):
        raise RuntimeError("camera analysis failed")


class FakeInstruments:
    lia = None


class MeasurementReadmeComputerVisionTests(unittest.TestCase):
    def build_laser_tab(self, output_path):
        camera_tab = FakeCameraTab()
        main_gui = type("MainGui", (), {"cameraControlTabObject": camera_tab})()
        return type(
            "LaserTab",
            (),
            {
                "main_gui": main_gui,
                "instruments": FakeInstruments(),
                "sample_selector_var": FakeVariable("NO SAMPLE"),
                "distanceInput": FakeVariable("5.0"),
                "angleInput": FakeVariable("0.0"),
                "freqInitialInput": FakeVariable("1"),
                "freqFinalInput": FakeVariable("1000"),
                "spacing_selector_var": FakeVariable("logspace"),
                "fileStorageLocation": FakeVariable(output_path),
            },
        )()

    def test_generated_readme_contains_camera_measurements(self):
        with tempfile.TemporaryDirectory() as output_path:
            generator = READMEGenerator()
            generator.update_info(self.build_laser_tab(output_path))
            generator.generate_readme(output_path)

            with open(os.path.join(output_path, "README.md")) as readme_file:
                contents = readme_file.read()

        self.assertIn("Detected Beam Distance: 28.50 px; approximately 0.655-0.969 um", contents)
        self.assertIn("Red Center: (10.25, 20.50) px", contents)
        self.assertIn("Red Beam Characterization: ellipse axes (4.00, 9.00) px", contents)
        self.assertIn("equivalent diameter 6.00 px", contents)
        self.assertIn("estimated equivalent diameter 0.138-0.204 um", contents)
        self.assertIn("Green Center: (30.00, 40.00) px", contents)

    def test_missing_camera_frame_is_reported(self):
        laser_tab = self.build_laser_tab("unused")
        laser_tab.main_gui.cameraControlTabObject = MissingFrameCameraTab()
        generator = READMEGenerator()

        generator._collect_computer_vision(laser_tab)

        self.assertIn("no camera frame", generator.computer_vision_status)
        self.assertEqual("NA", generator.beam_distance)

    def test_failed_collection_clears_previous_camera_measurements(self):
        scenarios = (
            ("camera unavailable", None, "camera tab is not initialized"),
            ("missing frame", MissingFrameCameraTab(), "no camera frame"),
            ("analysis failure", FailingCameraTab(), "camera analysis failed"),
        )
        vision_fields = (
            "red_center",
            "green_center",
            "red_characterization",
            "green_characterization",
            "beam_distance",
        )

        for name, camera_tab, expected_status in scenarios:
            with self.subTest(name=name):
                laser_tab = self.build_laser_tab("unused")
                generator = READMEGenerator()
                generator._collect_computer_vision(laser_tab)
                self.assertNotEqual("NA", generator.red_center)

                laser_tab.main_gui.cameraControlTabObject = camera_tab
                generator._collect_computer_vision(laser_tab)

                self.assertIn(expected_status, generator.computer_vision_status)
                for field in vision_fields:
                    self.assertEqual("NA", getattr(generator, field))


if __name__ == "__main__":
    unittest.main()
