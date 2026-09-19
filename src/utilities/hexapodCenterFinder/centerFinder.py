import math
import time

import numpy as np


class CenterFinderError(RuntimeError):
    pass


class SearchCancelled(CenterFinderError):
    pass


class HexapodCenterFinder:
    def __init__(
        self,
        hexapod,
        power_meter,
        threshold,
        step_size=0.1,
        max_travel=30.0,
        samples=3,
        settle_time=0.1,
        move_timeout=30.0,
        cancel_event=None,
        status_callback=None,
        sample_callback=None,
        coarse_step_size=None,
        save_position=True,
    ):
        if threshold <= 0:
            raise ValueError("Power threshold must be greater than zero.")
        if step_size <= 0 or max_travel <= 0:
            raise ValueError("Edge resolution and maximum travel must be greater than zero.")
        if coarse_step_size is None:
            coarse_step_size = step_size
        if coarse_step_size <= 0:
            raise ValueError("Coarse step size must be greater than zero.")
        if coarse_step_size < step_size:
            raise ValueError("Coarse step size must be at least the edge resolution.")
        if samples < 1:
            raise ValueError("Sample count must be at least one.")

        self.hexapod = hexapod
        self.power_meter = power_meter
        self.threshold = float(threshold)
        self.step_size = float(step_size)
        self.coarse_step_size = float(coarse_step_size)
        self.max_travel = float(max_travel)
        self.samples = int(samples)
        self.settle_time = float(settle_time)
        self.move_timeout = float(move_timeout)
        self.cancel_event = cancel_event
        self.status_callback = status_callback or (lambda _message: None)
        self.sample_callback = sample_callback or (lambda _power: None)
        self.save_position = save_position
        self.offset = [0.0, 0.0, 0.0]
        self.major_axis = None
        self.minor_axis = None

    def find_center(self):
        self._wait_for_hexapod()
        starting_position = self._get_hexapod_position()

        self.status_callback("Verifying that the laser is sensed")
        if not self._laser_is_sensed():
            raise CenterFinderError(
                f"Laser power is below the {self.threshold:g} W sensing threshold."
            )

        x_positive = self._find_first_edge(0, 1, "Searching for +X edge")
        x_negative = self._find_opposite_edge(0, -1, "Searching for -X edge")
        x_center = (x_positive + x_negative) / 2.0
        self._move_axis_to(0, x_center)

        self.status_callback("Verifying signal at X chord center")
        if not self._laser_is_sensed():
            raise CenterFinderError("Laser was not sensed at the X chord center.")

        y_positive = self._find_first_edge(1, 1, "Searching for +Y edge")
        y_negative = self._find_opposite_edge(1, -1, "Searching for -Y edge")
        y_center = (y_positive + y_negative) / 2.0
        self._move_axis_to(1, y_center)

        self.status_callback("Verifying signal at circle center")
        if not self._laser_is_sensed():
            raise CenterFinderError("Laser was not sensed at the calculated circle center.")

        x_positive = self._find_first_edge(0, 1, "Measuring +X edge")
        x_negative = self._find_opposite_edge(0, -1, "Measuring -X edge")
        self._move_axis_to(0, x_center)

        x_span = abs(x_positive - x_negative)
        y_span = abs(y_positive - y_negative)
        self.major_axis = max(x_span, y_span)
        self.minor_axis = min(x_span, y_span)

        laser_position = tuple(
            starting_position[index] + self.offset[index] for index in range(3)
        )
        if self.save_position:
            self.hexapod.set_laser_position(laser_position)
        print(f"Hexapod laser position: {laser_position}")
        self.status_callback(
            f"Center found; major axis {self.major_axis:g} mm, "
            f"minor axis {self.minor_axis:g} mm"
        )
        return laser_position

    def _find_first_edge(self, axis, direction, message):
        self.status_callback(f"{message} (roughing)")
        inside = self.offset[axis]
        while True:
            self._step(axis, direction, self.coarse_step_size)
            if not self._laser_is_sensed():
                return self._refine_edge(axis, inside, self.offset[axis], message)
            inside = self.offset[axis]

    def _find_opposite_edge(self, axis, direction, message):
        self.status_callback(f"{message} (roughing)")
        reacquired_laser = False
        inside = None
        while True:
            self._step(axis, direction, self.coarse_step_size)
            sensed = self._laser_is_sensed()
            if sensed:
                reacquired_laser = True
                inside = self.offset[axis]
            elif reacquired_laser:
                return self._refine_edge(axis, inside, self.offset[axis], message)

    def _refine_edge(self, axis, inside, outside, message):
        self.status_callback(f"{message} (bisection refinement)")
        while abs(outside - inside) > self.step_size:
            midpoint = (inside + outside) / 2.0
            self._move_axis_to(axis, midpoint)
            if self._laser_is_sensed():
                inside = midpoint
            else:
                outside = midpoint

        edge = (inside + outside) / 2.0
        self._move_axis_to(axis, edge)
        return edge

    def _step(self, axis, direction, distance):
        target = self.offset[axis] + direction * distance
        if abs(target) > self.max_travel + 1e-9:
            axis_name = "XYZ"[axis]
            raise CenterFinderError(
                f"No {axis_name} edge found within {self.max_travel:g} mm of the start."
            )
        self._move_axis_to(axis, target)

    def _move_axis_to(self, axis, target):
        self._check_cancelled()
        distance = target - self.offset[axis]
        movement = [0.0, 0.0, 0.0]
        movement[axis] = distance
        self.hexapod.translate(movement)
        self._wait_for_hexapod()
        self.offset[axis] = target
        if self.settle_time > 0:
            time.sleep(self.settle_time)

    def _laser_is_sensed(self):
        readings = []
        for sample_index in range(self.samples):
            self._check_cancelled()
            power = float(self.power_meter.read_power())
            readings.append(power)
            self.sample_callback(power)
            if sample_index + 1 < self.samples and self.settle_time > 0:
                time.sleep(self.settle_time)
        return sum(readings) / len(readings) >= self.threshold

    def _wait_for_hexapod(self):
        start_time = time.monotonic()
        while not getattr(self.hexapod, "ready_for_commands", False):
            self._check_cancelled()
            if time.monotonic() - start_time > self.move_timeout:
                raise TimeoutError("Hexapod movement timed out.")
            time.sleep(0.05)

    def _check_cancelled(self):
        if self.cancel_event is not None and self.cancel_event.is_set():
            raise SearchCancelled("Center search cancelled.")

    def _get_hexapod_position(self):
        status = getattr(self.hexapod, "status_dict", None)
        required_keys = ("s_mtp_tx", "s_mtp_ty", "s_mtp_tz")
        if not status or any(key not in status for key in required_keys):
            self.hexapod.getState()
            status = getattr(self.hexapod, "status_dict", None)
        if not status or any(key not in status for key in required_keys):
            raise CenterFinderError("Could not read the current hexapod position.")
        return tuple(float(status[key]) for key in required_keys)


class HexapodOrthogonalAligner:
    def __init__(
        self,
        hexapod,
        power_meter,
        height_offset,
        cancel_event=None,
        status_callback=None,
        sample_callback=None,
        refocus_callback=None,
        center_finder_class=HexapodCenterFinder,
        **center_settings,
    ):
        if height_offset <= 0:
            raise ValueError("Height offset must be greater than zero.")
        self.hexapod = hexapod
        self.power_meter = power_meter
        self.height_offset = float(height_offset)
        self.cancel_event = cancel_event
        self.status_callback = status_callback or (lambda _message: None)
        self.sample_callback = sample_callback or (lambda _power: None)
        self.refocus_callback = refocus_callback or (lambda _height: True)
        self.center_finder_class = center_finder_class
        self.center_settings = center_settings
        self.upper_center = None
        self.lower_center = None
        self.final_center = None
        self.rotation_correction = None

    def align(self):
        starting_pose = self._get_pose()
        calibration_applied = False
        try:
            self.status_callback("Moving to upper alignment height")
            self._translate_z(self.height_offset)
            self._confirm_refocus("upper")
            self.upper_center = self._find_center("Finding upper center")

            self.status_callback("Moving to lower alignment height")
            self._translate_z(-2.0 * self.height_offset)
            self._confirm_refocus("lower")
            self.lower_center = self._find_center("Finding lower center")

            self.rotation_correction = self._calculate_correction(starting_pose)
            original_height_center = tuple(
                (upper + lower) / 2.0
                for upper, lower in zip(self.upper_center, self.lower_center)
            )

            self.status_callback("Returning to starting pose")
            self._move_to_pose(starting_pose)
            self.status_callback(
                "Applying tilt correction "
                f"Rx {self.rotation_correction[0]:.6f} deg, "
                f"Ry {self.rotation_correction[1]:.6f} deg"
            )
            result = self.hexapod.rotateAroundPoint(
                original_height_center,
                self.rotation_correction,
            )
            self._require_success(result, "Tilt correction")

            self.final_center = self._find_center("Finding final corrected center")
            final_pose = self._get_pose()
            self.hexapod.set_laser_calibration(self.final_center, final_pose)
            calibration_applied = True
            self.status_callback("Orthogonal alignment complete")
            return self.rotation_correction
        finally:
            if not calibration_applied:
                self.status_callback("Restoring starting pose")
                self._move_to_pose(starting_pose)

    def _find_center(self, message):
        self.status_callback(message)
        finder = self.center_finder_class(
            self.hexapod,
            self.power_meter,
            cancel_event=self.cancel_event,
            status_callback=self.status_callback,
            sample_callback=self.sample_callback,
            save_position=False,
            **self.center_settings,
        )
        return finder.find_center()

    def _confirm_refocus(self, height):
        self.status_callback(f"Waiting for laser refocus confirmation at {height} height")
        if not self.refocus_callback(height):
            raise SearchCancelled("Orthogonal alignment cancelled while waiting for refocus.")

    def _calculate_correction(self, starting_pose):
        delta = np.asarray(self.upper_center) - np.asarray(self.lower_center)
        if delta[2] <= 0:
            raise CenterFinderError("Upper and lower center heights are invalid.")
        expected_separation = 2.0 * self.height_offset
        baseline_error = abs(delta[2] - expected_separation)
        if baseline_error - 0.002 > 1e-12:
            raise CenterFinderError(
                "Measured center heights do not match the requested alignment baseline."
            )

        x_slope = delta[0] / delta[2]
        y_slope = delta[1] / delta[2]

        # Remove the current Z rotation before converting the measured lab-frame
        # centerline into the controller's Rx/Ry Euler angles.
        rz = math.radians(starting_pose[5])
        local_x_slope = math.cos(rz) * x_slope + math.sin(rz) * y_slope
        local_y_slope = -math.sin(rz) * x_slope + math.cos(rz) * y_slope
        ry = math.atan(local_x_slope)
        rx = -math.atan2(local_y_slope, math.sqrt(1.0 + local_x_slope ** 2))
        return np.degrees(np.array([rx, ry, 0.0]))

    def _translate_z(self, distance):
        result = self.hexapod.translate(np.array([0.0, 0.0, distance]))
        self._require_success(result, "Height movement")

    def _move_to_pose(self, target_pose):
        current_pose = self._get_pose()
        delta = np.asarray(target_pose) - np.asarray(current_pose)
        if np.any(np.abs(delta) > 1e-12):
            result = self.hexapod.compoundMove(delta[:3], delta[3:])
            self._require_success(result, "Pose restoration")

    @staticmethod
    def _require_success(result, operation):
        if result != "Success.":
            raise CenterFinderError(f"{operation} failed: {result}")

    def _get_pose(self):
        pose = getattr(self.hexapod, "position", None)
        if pose is None or len(pose) != 6 or any(value is None for value in pose):
            self.hexapod.getState()
            if hasattr(self.hexapod, "logPosition"):
                self.hexapod.logPosition()
            pose = getattr(self.hexapod, "position", None)
        try:
            pose = tuple(float(value) for value in pose)
        except (TypeError, ValueError):
            raise CenterFinderError("Could not read the complete hexapod pose.")
        if len(pose) != 6 or not np.all(np.isfinite(pose)):
            raise CenterFinderError("Could not read the complete hexapod pose.")
        return pose
