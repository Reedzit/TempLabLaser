import numpy as np


HOME_FACE_NORMAL = np.array([0.0, 0.0, 1.0])
LASER_DIRECTION = HOME_FACE_NORMAL


def rotation_matrix(rx, ry, rz):
    rx, ry, rz = np.radians([rx, ry, rz])
    x_rotation = np.array([
        [1.0, 0.0, 0.0],
        [0.0, np.cos(rx), -np.sin(rx)],
        [0.0, np.sin(rx), np.cos(rx)],
    ])
    y_rotation = np.array([
        [np.cos(ry), 0.0, np.sin(ry)],
        [0.0, 1.0, 0.0],
        [-np.sin(ry), 0.0, np.cos(ry)],
    ])
    z_rotation = np.array([
        [np.cos(rz), -np.sin(rz), 0.0],
        [np.sin(rz), np.cos(rz), 0.0],
        [0.0, 0.0, 1.0],
    ])
    return z_rotation @ y_rotation @ x_rotation


def _pose_transform(hexapod_position, reference_pose=None):
    pose = np.asarray(hexapod_position, dtype=float)
    if pose.shape != (6,) or not np.all(np.isfinite(pose)):
        raise ValueError("The hexapod position must contain six finite coordinates.")
    translation = pose[:3]
    rotation = rotation_matrix(*pose[3:])
    if reference_pose is None:
        return translation, rotation
    reference = np.asarray(reference_pose, dtype=float)
    if reference.shape != (6,) or not np.all(np.isfinite(reference)):
        raise ValueError("The calibration reference pose must contain six finite coordinates.")
    relative_rotation = rotation @ rotation_matrix(*reference[3:]).T
    return translation - reference[:3], relative_rotation


def laser_spot_on_face(home_laser_position, hexapod_position, reference_pose=None):
    home_spot = np.asarray(home_laser_position, dtype=float)
    translation, rotation = _pose_transform(hexapod_position, reference_pose)
    if home_spot.shape != (3,) or not np.all(np.isfinite(home_spot)):
        raise ValueError("The home laser position must contain three finite coordinates.")

    moved_face_point = translation + rotation @ home_spot
    moved_face_normal = rotation @ HOME_FACE_NORMAL
    incidence = np.dot(moved_face_normal, LASER_DIRECTION)
    if abs(incidence) < 1e-9:
        raise ValueError("The laser is parallel to the hexapod face.")

    distance_along_beam = (
        np.dot(moved_face_normal, moved_face_point - home_spot) / incidence
    )
    intersection = home_spot + distance_along_beam * LASER_DIRECTION

    # Return the material coordinate on the moving face, not the fixed lab coordinate.
    face_spot = rotation.T @ (intersection - translation)
    return tuple(float(value) for value in face_spot)


def rotation_compensation_for_face_spot(
    home_laser_position,
    hexapod_position,
    rotation_delta,
    reference_pose=None,
):
    pose = np.asarray(hexapod_position, dtype=float)
    _translation, current_rotation = _pose_transform(pose, reference_pose)
    rotation_delta = np.asarray(rotation_delta, dtype=float)
    if rotation_delta.shape != (3,) or not np.all(np.isfinite(rotation_delta)):
        raise ValueError("The rotation must contain three finite angles.")

    face_spot = np.asarray(
        laser_spot_on_face(home_laser_position, pose, reference_pose)
    )
    final_pose = pose.copy()
    final_pose[3:] += rotation_delta
    _translation, final_rotation = _pose_transform(final_pose, reference_pose)
    compensation = current_rotation @ face_spot - final_rotation @ face_spot
    return tuple(float(value) for value in compensation)
