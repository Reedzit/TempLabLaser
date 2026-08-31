import math
import unittest

import numpy as np

from src.utilities.hexapodCenterFinder.centerFinder import (
    CenterFinderError,
    HexapodOrthogonalAligner,
    SearchCancelled,
)
from src.hexapod.laserGeometry import rotation_matrix


class FakeHexapod:
    def __init__(self, position=(10, 20, 30, 1, 2, 0)):
        self.position = tuple(float(value) for value in position)
        self.moves = []
        self.rotations = []
        self.calibration = None

    def translate(self, movement):
        movement = np.asarray(movement, dtype=float)
        pose = np.asarray(self.position)
        pose[:3] += movement
        self.position = tuple(pose)
        self.moves.append(("translate", tuple(movement)))
        return "Success."

    def compoundMove(self, movement, rotation):
        movement = np.asarray(movement, dtype=float)
        rotation = np.asarray(rotation, dtype=float)
        pose = np.asarray(self.position)
        pose[:3] += movement
        pose[3:] += rotation
        self.position = tuple(pose)
        self.moves.append(("compound", tuple(movement), tuple(rotation)))
        return "Success."

    def rotateAroundPoint(self, point, rotation):
        self.rotations.append((tuple(point), tuple(rotation), self.position))
        return self.compoundMove((0, 0, 0), rotation)

    def set_laser_calibration(self, position, reference_pose):
        self.calibration = (tuple(position), tuple(reference_pose))


class SequenceCenterFinder:
    centers = []
    calls = []

    def __init__(self, hexapod, _power_meter, **settings):
        self.hexapod = hexapod
        self.settings = settings
        self.__class__.calls.append(settings)

    def find_center(self):
        center = self.__class__.centers.pop(0)
        if isinstance(center, Exception):
            raise center
        pose = list(self.hexapod.position)
        pose[:3] = center
        self.hexapod.position = tuple(pose)
        return tuple(center)


class HexapodOrthogonalAlignmentTests(unittest.TestCase):
    def setUp(self):
        SequenceCenterFinder.calls = []

    def make_aligner(self, hexapod, **options):
        return HexapodOrthogonalAligner(
            hexapod,
            object(),
            height_offset=5,
            center_finder_class=SequenceCenterFinder,
            threshold=0.5,
            step_size=0.1,
            **options,
        )

    def test_two_centers_produce_tilt_and_new_digital_home(self):
        hexapod = FakeHexapod()
        SequenceCenterFinder.centers = [
            (10.4, 19.8, 35.0),
            (9.6, 20.2, 25.0),
            (10.05, 20.03, 30.0),
        ]
        aligner = self.make_aligner(hexapod)

        correction = aligner.align()

        expected = (
            -math.degrees(math.atan2(-0.04, math.sqrt(1.0 + 0.08 ** 2))),
            math.degrees(math.atan2(0.8, 10.0)),
            0.0,
        )
        np.testing.assert_allclose(expected, correction, atol=1e-12)
        pivot, applied_rotation, pose_before_rotation = hexapod.rotations[0]
        np.testing.assert_allclose((10, 20, 30), pivot, atol=1e-12)
        np.testing.assert_allclose(expected, applied_rotation, atol=1e-12)
        np.testing.assert_allclose((10, 20, 30, 1, 2, 0), pose_before_rotation, atol=1e-12)
        self.assertEqual((10.05, 20.03, 30.0), hexapod.calibration[0])
        self.assertEqual(hexapod.position, hexapod.calibration[1])
        self.assertTrue(all(call["save_position"] is False for call in SequenceCenterFinder.calls))

    def test_failed_measurement_restores_start_without_calibrating(self):
        starting_pose = (10, 20, 30, 1, 2, 0)
        hexapod = FakeHexapod(starting_pose)
        SequenceCenterFinder.centers = [
            (10.4, 19.8, 35.0),
            CenterFinderError("lower center failed"),
        ]

        with self.assertRaisesRegex(CenterFinderError, "lower center failed"):
            self.make_aligner(hexapod).align()

        np.testing.assert_allclose(starting_pose, hexapod.position, atol=1e-12)
        self.assertIsNone(hexapod.calibration)
        self.assertEqual([], hexapod.rotations)

    def test_waits_for_refocus_at_each_measurement_height(self):
        hexapod = FakeHexapod()
        confirmations = []
        SequenceCenterFinder.centers = [
            (10.4, 19.8, 35.0),
            (9.6, 20.2, 25.0),
            (10.05, 20.03, 30.0),
        ]

        self.make_aligner(
            hexapod,
            refocus_callback=lambda height: confirmations.append(
                (height, hexapod.position)
            ) or True,
        ).align()

        self.assertEqual(["upper", "lower"], [item[0] for item in confirmations])
        self.assertEqual(35.0, confirmations[0][1][2])
        self.assertEqual(25.0, confirmations[1][1][2])

    def test_cancelled_refocus_confirmation_restores_start(self):
        starting_pose = (10, 20, 30, 1, 2, 0)
        hexapod = FakeHexapod(starting_pose)

        with self.assertRaisesRegex(SearchCancelled, "waiting for refocus"):
            self.make_aligner(
                hexapod,
                refocus_callback=lambda _height: False,
            ).align()

        np.testing.assert_allclose(starting_pose, hexapod.position, atol=1e-12)
        self.assertIsNone(hexapod.calibration)

    def test_angle_calculation_exactly_cancels_both_tilts_with_z_rotation(self):
        rx, ry, rz = 3.0, -4.0, 20.0
        normal = rotation_matrix(rx, ry, rz) @ np.array([0.0, 0.0, 1.0])
        slopes = -normal[:2] / normal[2]
        aligner = self.make_aligner(FakeHexapod())
        aligner.lower_center = (0.0, 0.0, 25.0)
        aligner.upper_center = (slopes[0] * 10, slopes[1] * 10, 35.0)

        correction = aligner._calculate_correction((0, 0, 30, rx, ry, rz))

        np.testing.assert_allclose((-rx, -ry, 0), correction, atol=1e-12)

    def test_height_baseline_allows_two_microns_of_error(self):
        aligner = self.make_aligner(FakeHexapod())
        aligner.lower_center = (0.0, 0.0, 25.0)
        aligner.upper_center = (0.0, 0.0, 35.002)

        correction = aligner._calculate_correction((0, 0, 30, 0, 0, 0))

        np.testing.assert_allclose((0, 0, 0), correction, atol=1e-12)

    def test_height_baseline_rejects_more_than_two_microns_of_error(self):
        aligner = self.make_aligner(FakeHexapod())
        aligner.lower_center = (0.0, 0.0, 25.0)
        aligner.upper_center = (0.0, 0.0, 35.0021)

        with self.assertRaisesRegex(CenterFinderError, "alignment baseline"):
            aligner._calculate_correction((0, 0, 30, 0, 0, 0))

    def test_rejects_nonpositive_height_offset(self):
        with self.assertRaisesRegex(ValueError, "greater than zero"):
            HexapodOrthogonalAligner(FakeHexapod(), object(), 0)


if __name__ == "__main__":
    unittest.main()
