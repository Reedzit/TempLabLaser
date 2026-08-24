import unittest

import cv2
import numpy as np

from src.gui_tabs.cameraControlTab import CameraControlTab


class FourthAttemptDetector:
    def __init__(self):
        self.images = []

    def detectMarkers(self, image):
        self.images.append(image.copy())
        if len(self.images) < 4:
            return [], None, []
        corners = [np.array([[[10, 10], [80, 10], [80, 80], [10, 80]]], dtype=np.float32)]
        return corners, np.array([[7]], dtype=np.int32), []


@unittest.skipUnless(hasattr(cv2, "aruco"), "OpenCV ArUco module is not installed")
class CameraArucoDetectionTests(unittest.TestCase):
    def test_detected_marker_is_annotated_without_changing_source_frame(self):
        tab = CameraControlTab.__new__(CameraControlTab)
        tab.aruco_dictionary = None
        tab.aruco_detector = None
        tab.setup_aruco_detector()

        if hasattr(cv2.aruco, "generateImageMarker"):
            marker = cv2.aruco.generateImageMarker(tab.aruco_dictionary, 7, 200)
        else:
            marker = cv2.aruco.drawMarker(tab.aruco_dictionary, 7, 200)
        frame = np.full((300, 300, 3), 255, dtype=np.uint8)
        frame[50:250, 50:250] = cv2.cvtColor(marker, cv2.COLOR_GRAY2BGR)
        original = frame.copy()

        annotated = tab.annotate_aruco_markers(frame)

        self.assertTrue(np.array_equal(frame, original))
        self.assertFalse(np.array_equal(annotated, original))

    def test_frame_without_marker_is_returned_unchanged(self):
        tab = CameraControlTab.__new__(CameraControlTab)
        tab.aruco_dictionary = None
        tab.aruco_detector = None
        tab.setup_aruco_detector()
        frame = np.full((200, 200, 3), 255, dtype=np.uint8)

        annotated = tab.annotate_aruco_markers(frame)

        self.assertTrue(np.array_equal(annotated, frame))

    def test_aruco_original_marker_is_detected(self):
        tab = CameraControlTab.__new__(CameraControlTab)
        tab.aruco_dictionary = None
        tab.aruco_detector = None
        tab.aruco_detectors = []
        tab.setup_aruco_detector()
        dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_ARUCO_ORIGINAL)
        if hasattr(cv2.aruco, "generateImageMarker"):
            marker = cv2.aruco.generateImageMarker(dictionary, 7, 270)
        else:
            marker = cv2.aruco.drawMarker(dictionary, 7, 270)
        frame = np.full((350, 350, 3), 255, dtype=np.uint8)
        frame[40:310, 40:310] = cv2.cvtColor(marker, cv2.COLOR_GRAY2BGR)

        annotated = tab.annotate_aruco_markers(frame)

        self.assertFalse(np.array_equal(annotated, frame))

    def test_preprocessing_fallbacks_run_until_a_marker_is_detected(self):
        tab = CameraControlTab.__new__(CameraControlTab)
        tab.aruco_dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_ARUCO_ORIGINAL)
        tab.aruco_detector = FourthAttemptDetector()
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        frame[:, :, 2] = np.tile(np.arange(100, dtype=np.uint8), (100, 1))

        annotated = tab.annotate_aruco_markers(frame)

        self.assertEqual(4, len(tab.aruco_detector.images))
        self.assertTrue(set(np.unique(tab.aruco_detector.images[-1])).issubset({0, 255}))
        self.assertFalse(np.array_equal(annotated, frame))

    def test_bandpass_suppresses_fine_texture_and_preserves_dark_region(self):
        tab = CameraControlTab.__new__(CameraControlTab)
        checkerboard = (np.indices((160, 160)).sum(axis=0) % 2) * 80
        red = np.clip(170 + checkerboard, 0, 255).astype(np.uint8)
        red[50:110, 50:110] = np.clip(red[50:110, 50:110] - 100, 0, 255)
        frame = np.zeros((160, 160, 3), dtype=np.uint8)
        frame[:, :, 2] = red

        candidates = list(tab.build_aruco_detection_images(frame))
        bandpassed = candidates[1][0]

        original_texture_std = float(red[10:40, 10:40].std())
        filtered_texture_std = float(bandpassed[10:40, 10:40].std())
        outside_mean = float(bandpassed[10:40, 10:40].mean())
        marker_mean = float(bandpassed[65:95, 65:95].mean())
        self.assertLess(filtered_texture_std, original_texture_std * 0.25)
        self.assertGreater(outside_mean - marker_mean, 20)


if __name__ == "__main__":
    unittest.main()
