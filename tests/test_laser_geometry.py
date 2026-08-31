import unittest

import numpy as np

from src.hexapod.laserGeometry import (
    laser_spot_on_face,
    rotation_compensation_for_face_spot,
    rotation_matrix,
)


class LaserGeometryTests(unittest.TestCase):
    def test_home_pose_returns_calibrated_spot(self):
        spot = laser_spot_on_face((1, 2, 3), (0, 0, 0, 0, 0, 0))

        np.testing.assert_allclose((1, 2, 3), spot, atol=1e-12)

    def test_translation_changes_material_point_under_fixed_beam(self):
        spot = laser_spot_on_face((1, 2, 3), (0.25, -0.5, 4, 0, 0, 0))

        np.testing.assert_allclose((0.75, 2.5, 3), spot, atol=1e-12)

    def test_tilt_returns_spot_on_rotated_face(self):
        spot = laser_spot_on_face((1, 0, 0), (0, 0, 0, 0, 30, 0))

        np.testing.assert_allclose((2 / np.sqrt(3), 0, 0), spot, atol=1e-12)

    def test_rotation_compensation_keeps_same_face_spot(self):
        home_spot = np.array([1.0, -2.0, 0.5])
        rotation = rotation_matrix(5, -7, 3)
        compensation = home_spot - rotation @ home_spot

        spot = laser_spot_on_face(
            home_spot,
            (*compensation, 5, -7, 3),
        )

        np.testing.assert_allclose(home_spot, spot, atol=1e-12)

    def test_compensation_preserves_current_spot_from_non_home_pose(self):
        home_spot = (1.0, -2.0, 0.5)
        pose = np.array([0.25, -0.4, 1.0, 3.0, -4.0, 5.0])
        rotation_delta = np.array([2.0, 1.0, -3.0])
        initial_spot = laser_spot_on_face(home_spot, pose)
        compensation = rotation_compensation_for_face_spot(
            home_spot,
            pose,
            rotation_delta,
        )
        final_pose = np.concatenate((
            pose[:3] + compensation,
            pose[3:] + rotation_delta,
        ))

        final_spot = laser_spot_on_face(home_spot, final_pose)

        np.testing.assert_allclose(initial_spot, final_spot, atol=1e-12)

    def test_parallel_face_has_no_unique_intersection(self):
        with self.assertRaisesRegex(ValueError, "parallel"):
            laser_spot_on_face((0, 0, 0), (0, 0, 0, 0, 90, 0))

    def test_calibrated_reference_pose_is_treated_as_digital_home(self):
        reference_pose = (10, -5, 3, 2, -4, 1)

        spot = laser_spot_on_face((1, 2, 3), reference_pose, reference_pose)
        compensation = rotation_compensation_for_face_spot(
            (1, 0, 0),
            reference_pose,
            (0, 0, 90),
            reference_pose,
        )

        np.testing.assert_allclose((1, 2, 3), spot, atol=1e-12)
        np.testing.assert_allclose((1, -1, 0), compensation, atol=1e-12)


if __name__ == "__main__":
    unittest.main()
