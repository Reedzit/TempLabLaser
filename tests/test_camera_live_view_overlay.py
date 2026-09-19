import unittest
from unittest.mock import Mock, patch

import numpy as np

from src.gui_tabs.cameraControlTab import CameraControlTab


class CameraLiveViewOverlayTests(unittest.TestCase):
    def test_measurement_vision_adds_estimated_micron_distance(self):
        tab = CameraControlTab.__new__(CameraControlTab)
        tab.camera_manager = Mock()
        tab.camera_manager.get_latest_frame.return_value = np.zeros((20, 20, 3), dtype=np.uint8)
        tab.contour_selection = Mock()
        tab.contour_selection.get.return_value = 0
        tab.s_min = Mock()
        tab.s_min.get.return_value = 50
        tab.v_min = Mock()
        tab.v_min.get.return_value = 50
        detection = {"red": None, "green": None, "distance_px": 100.0}

        with patch("src.gui_tabs.cameraControlTab.detect_red_green_lasers", return_value=detection):
            result = tab.collect_measurement_vision()

        self.assertAlmostEqual(2.3, result["distance_microns"][0])
        self.assertAlmostEqual(3.4, result["distance_microns"][1])
        self.assertIs(result, tab.last_detection)

    def test_cursor_coordinates_map_to_original_frame_with_letterboxing(self):
        coordinates = CameraControlTab.map_cursor_to_source(
            250,
            200,
            widget_size=(500, 400),
            display_size=(400, 200),
            source_size=(800, 400),
        )

        self.assertEqual((400, 200), coordinates)

    def test_cursor_outside_displayed_image_has_no_coordinates(self):
        coordinates = CameraControlTab.map_cursor_to_source(
            20,
            20,
            widget_size=(500, 400),
            display_size=(400, 200),
            source_size=(800, 400),
        )

        self.assertIsNone(coordinates)

    def test_scale_range_uses_camera_conversion_limits(self):
        minimum, maximum = CameraControlTab.scale_bar_micron_range(200)

        self.assertAlmostEqual(4.6, minimum)
        self.assertAlmostEqual(6.8, maximum)

    def test_scale_bar_annotation_does_not_modify_source_frame(self):
        tab = CameraControlTab.__new__(CameraControlTab)
        frame = np.zeros((200, 800, 3), dtype=np.uint8)
        original = frame.copy()

        annotated = tab.annotate_scale_bar(frame, source_width=1600)

        self.assertTrue(np.array_equal(frame, original))
        self.assertFalse(np.array_equal(annotated, original))


if __name__ == "__main__":
    unittest.main()
