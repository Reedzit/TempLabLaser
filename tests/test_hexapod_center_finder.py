import unittest

from src.utilities.hexapodCenterFinder.centerFinder import CenterFinderError, HexapodCenterFinder


class FakeHexapod:
    def __init__(self, position=(10.0, 20.0, 3.0)):
        self.position = list(position)
        self.ready_for_commands = True
        self.laser_position = None
        self.movements = []
        self.status_dict = {}
        self._update_status()

    def translate(self, movement):
        self.movements.append(tuple(movement))
        for axis, distance in enumerate(movement):
            self.position[axis] += distance
        self._update_status()

    def getState(self):
        self._update_status()

    def set_laser_position(self, position):
        self.laser_position = tuple(position)
        return self.laser_position

    def _update_status(self):
        self.status_dict.update(
            s_mtp_tx=self.position[0],
            s_mtp_ty=self.position[1],
            s_mtp_tz=self.position[2],
        )


class CircularPowerMeter:
    def __init__(self, hexapod, center=(11.0, 19.0), radius=3.0):
        self.hexapod = hexapod
        self.center = center
        self.radius = radius

    def read_power(self):
        x, y = self.hexapod.position[:2]
        distance_squared = (x - self.center[0]) ** 2 + (y - self.center[1]) ** 2
        return 1.0 if distance_squared <= self.radius ** 2 else 0.0


class EllipticalPowerMeter:
    def __init__(self, hexapod, center=(11.0, 19.0), x_radius=4.0, y_radius=2.0):
        self.hexapod = hexapod
        self.center = center
        self.x_radius = x_radius
        self.y_radius = y_radius

    def read_power(self):
        x, y = self.hexapod.position[:2]
        normalized_distance = (
            ((x - self.center[0]) / self.x_radius) ** 2
            + ((y - self.center[1]) / self.y_radius) ** 2
        )
        return 1.0 if normalized_distance <= 1.0 else 0.0


class HexapodCenterFinderTests(unittest.TestCase):
    def make_finder(self, hexapod, power_meter, **overrides):
        settings = {
            "threshold": 0.5,
            "step_size": 1.0,
            "max_travel": 10.0,
            "samples": 1,
            "settle_time": 0.0,
        }
        settings.update(overrides)
        return HexapodCenterFinder(hexapod, power_meter, **settings)

    def test_finds_circle_center_and_stores_absolute_position(self):
        hexapod = FakeHexapod()
        finder = self.make_finder(hexapod, CircularPowerMeter(hexapod))

        result = finder.find_center()

        self.assertEqual((11.0, 19.0, 3.0), result)
        self.assertEqual(result, hexapod.laser_position)
        self.assertEqual(list(result), hexapod.position)

    def test_rejects_search_when_laser_is_not_initially_sensed(self):
        hexapod = FakeHexapod()
        power_meter = CircularPowerMeter(hexapod, center=(100.0, 100.0))
        finder = self.make_finder(hexapod, power_meter)

        with self.assertRaisesRegex(CenterFinderError, "below"):
            finder.find_center()

        self.assertIsNone(hexapod.laser_position)
        self.assertEqual([10.0, 20.0, 3.0], hexapod.position)

    def test_stops_when_edge_exceeds_maximum_travel(self):
        hexapod = FakeHexapod()
        power_meter = CircularPowerMeter(hexapod, center=(10.0, 20.0), radius=100.0)
        finder = self.make_finder(hexapod, power_meter, max_travel=2.0)

        with self.assertRaisesRegex(CenterFinderError, "No X edge found"):
            finder.find_center()

        self.assertIsNone(hexapod.laser_position)

    def test_roughs_and_fine_tunes_each_edge(self):
        hexapod = FakeHexapod()
        statuses = []
        power_meter = CircularPowerMeter(hexapod, center=(10.7, 19.4), radius=3.2)
        finder = self.make_finder(
            hexapod,
            power_meter,
            coarse_step_size=2.0,
            step_size=0.1,
            status_callback=statuses.append,
        )

        result = finder.find_center()

        self.assertAlmostEqual(10.7, result[0], delta=0.1)
        self.assertAlmostEqual(19.4, result[1], delta=0.1)
        distances = [abs(distance) for movement in hexapod.movements for distance in movement if distance]
        self.assertTrue(any(abs(distance - 2.0) < 1e-9 for distance in distances))
        self.assertTrue(any(abs(distance - 0.1) < 1e-9 for distance in distances))
        self.assertEqual(6, sum("(roughing)" in status for status in statuses))
        self.assertEqual(6, sum("(fine tuning)" in status for status in statuses))

    def test_reports_major_and_minor_axes_through_the_center(self):
        hexapod = FakeHexapod(position=(10.0, 20.0, 3.0))
        finder = self.make_finder(
            hexapod,
            EllipticalPowerMeter(hexapod),
            coarse_step_size=2.0,
            step_size=0.1,
        )

        finder.find_center()

        self.assertAlmostEqual(8.0, finder.major_axis, delta=0.2)
        self.assertAlmostEqual(4.0, finder.minor_axis, delta=0.2)

    def test_rejects_rough_step_smaller_than_fine_step(self):
        hexapod = FakeHexapod()

        with self.assertRaisesRegex(ValueError, "at least the fine step size"):
            self.make_finder(
                hexapod,
                CircularPowerMeter(hexapod),
                coarse_step_size=0.5,
                step_size=1.0,
            )


if __name__ == "__main__":
    unittest.main()
