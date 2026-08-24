import time


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
    ):
        if threshold <= 0:
            raise ValueError("Power threshold must be greater than zero.")
        if step_size <= 0 or max_travel <= 0:
            raise ValueError("Fine step size and maximum travel must be greater than zero.")
        if coarse_step_size is None:
            coarse_step_size = step_size
        if coarse_step_size <= 0:
            raise ValueError("Coarse step size must be greater than zero.")
        if coarse_step_size < step_size:
            raise ValueError("Coarse step size must be at least the fine step size.")
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
                return self._refine_edge(axis, direction, inside, self.offset[axis], message)
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
                return self._refine_edge(axis, direction, inside, self.offset[axis], message)

    def _refine_edge(self, axis, direction, inside, outside, message):
        self.status_callback(f"{message} (fine tuning)")
        self._move_axis_to(axis, inside)
        while True:
            remaining = direction * (outside - self.offset[axis])
            distance = min(self.step_size, remaining)
            self._step(axis, direction, distance)
            if not self._laser_is_sensed():
                return self.offset[axis]

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
