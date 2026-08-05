import unittest

from src.utilities.hexapodCenterFinder.centerFinder import CenterFinderError, HexapodCenterFinder


class FakeHexapod:
    def __init__(self, position=(10.0, 20.0, 3.0)):
        self.position = list(position)
        self.ready_for_commands = True
        self.laser_position = None
        self.status_dict = {}
        self._update_status()

    def translate(self, movement):
        for axis, distance in enumerate(movement):
            self.position[axis] += distance
        self._update_status()

    def getState(self):
        self._update_status()

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


if __name__ == "__main__":
    unittest.main()
