import unittest
from types import SimpleNamespace

import numpy as np

from src.gui_tabs.automationHexapodTab import HexapodAutomationTab
from src.gui_tabs.automationManagementTab import AutomationManagerTab
from src.gui_tabs.cameraControlTab import CameraControlTab
from src.gui_tabs.rasteringTab import RasteringTab
from src.hexapod.hexapodControl2 import HexapodControl


class FakeButton:
    def __init__(self):
        self.state = None

    def configure(self, **options):
        if "state" in options:
            self.state = options["state"]

    def __setitem__(self, key, value):
        if key == "state":
            self.state = value


class FakeCommandTab:
    def __init__(self):
        self.ready = None

    def update_hexapod_command_controls(self, ready):
        self.ready = ready


class FakeLabel:
    def __init__(self):
        self.text = None
        self.fg = None

    def config(self, **options):
        self.text = options.get("text", self.text)

    def configure(self, **options):
        self.text = options.get("text", self.text)
        self.fg = options.get("fg", self.fg)


class FakeDisplay:
    def __init__(self):
        self.values = None

    def set_values(self, values):
        self.values = values

    def clear(self):
        self.values = None


class FakeValue:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value


class HexapodCommandControlTests(unittest.TestCase):
    def test_main_controls_and_other_tabs_follow_ready_state(self):
        tab = HexapodAutomationTab.__new__(HexapodAutomationTab)
        command_button_names = (
            "homeHexapodButton",
            "controlOnHexapodButton",
            "controlOffHexapodButton",
            "centerFinderButton",
            "manualTranslationButton",
            "manualTranslationButtonReverse",
            "manualRotationButton",
            "printStateButton",
        )
        for name in command_button_names:
            setattr(tab, name, FakeButton())
        tab.connectHexapodButton = FakeButton()
        tab.main_gui = SimpleNamespace(
            rasteringTabObject=FakeCommandTab(),
            cameraControlTabObject=FakeCommandTab(),
            automationTabObject=FakeCommandTab(),
        )

        tab.update_command_controls(connected=True, ready=False)

        self.assertTrue(all(getattr(tab, name).state == "disabled" for name in command_button_names))
        self.assertEqual("disabled", tab.connectHexapodButton.state)
        self.assertFalse(tab.main_gui.rasteringTabObject.ready)
        self.assertFalse(tab.main_gui.cameraControlTabObject.ready)
        self.assertFalse(tab.main_gui.automationTabObject.ready)

        tab.update_command_controls(connected=True, ready=True)

        self.assertTrue(all(getattr(tab, name).state == "normal" for name in command_button_names))
        self.assertTrue(tab.main_gui.rasteringTabObject.ready)
        self.assertTrue(tab.main_gui.cameraControlTabObject.ready)
        self.assertTrue(tab.main_gui.automationTabObject.ready)

    def test_workflow_controls_remain_disabled_while_locally_running(self):
        raster = RasteringTab.__new__(RasteringTab)
        raster.startScanButton = FakeButton()
        raster.returnOriginButton = FakeButton()
        raster.scan_running = True
        raster.update_hexapod_command_controls(True)
        self.assertEqual("disabled", raster.startScanButton.state)
        self.assertEqual("disabled", raster.returnOriginButton.state)

        camera = CameraControlTab.__new__(CameraControlTab)
        camera.autofocus_button = FakeButton()
        camera.focus_laser_button = FakeButton()
        camera.autofocus_running = True
        camera.focus_laser_running = False
        camera.update_hexapod_command_controls(True)
        self.assertEqual("disabled", camera.autofocus_button.state)
        self.assertEqual("disabled", camera.focus_laser_button.state)

    def test_automation_start_controls_follow_ready_state(self):
        tab = AutomationManagerTab.__new__(AutomationManagerTab)
        tab.startAutomationButton = FakeButton()
        tab.startFocussingButton = FakeButton()

        tab.update_hexapod_command_controls(False)
        self.assertEqual("disabled", tab.startAutomationButton.state)
        self.assertEqual("disabled", tab.startFocussingButton.state)

        tab.update_hexapod_command_controls(True)
        self.assertEqual("normal", tab.startAutomationButton.state)
        self.assertEqual("normal", tab.startFocussingButton.state)

    def test_home_task_keeps_controller_busy(self):
        controller = HexapodControl.__new__(HexapodControl)
        controller.ready_for_commands = True
        controller.getState = lambda: None
        controller.status_dict = {
            "s_hexa_bits": {
                "Motion task running": False,
                "Home task running": True,
            }
        }

        self.assertFalse(controller.checkStatus())
        self.assertFalse(controller.ready_for_commands)

    def test_incomplete_status_keeps_controller_busy(self):
        controller = HexapodControl.__new__(HexapodControl)
        controller.ready_for_commands = True
        controller.getState = lambda: setattr(controller, "status_dict", {})
        controller.status_dict = None

        self.assertFalse(controller.checkStatus())
        self.assertFalse(controller.ready_for_commands)

    def test_command_resolution_retries_incomplete_status(self):
        controller = HexapodControl.__new__(HexapodControl)
        controller.ready_for_commands = False
        controller.commandResolutionThread = None
        states = iter(({}, {
            "s_hexa_bits": {
                "Motion task running": False,
                "Home task running": False,
            }
        }))
        state_reads = []

        def get_state():
            controller.status_dict = next(states)
            state_reads.append(controller.status_dict)

        controller.getState = get_state
        controller.logPosition = lambda: None

        controller.waitForCommandResolution()
        thread = controller.commandResolutionThread
        thread.join(timeout=2)

        self.assertFalse(thread.is_alive())
        self.assertEqual(2, len(state_reads))
        self.assertTrue(controller.ready_for_commands)
        self.assertIsNone(controller.commandResolutionThread)

    def test_rotate_around_laser_compensates_for_rotated_offset(self):
        controller = HexapodControl.__new__(HexapodControl)
        controller.laser_position = (1.0, 0.0, 0.0)
        controller.position = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        moves = []
        controller.compoundMove = lambda movement, rotation: moves.append((movement, rotation))

        controller.rotateAroundLaser(np.array([0.0, 0.0, 90.0]))

        movement, rotation = moves[0]
        np.testing.assert_allclose(movement, (1.0, -1.0, 0.0), atol=1e-12)
        np.testing.assert_allclose(rotation, (0.0, 0.0, 90.0))

    def test_rotate_around_laser_uses_current_face_spot(self):
        controller = HexapodControl.__new__(HexapodControl)
        controller.laser_position = (1.0, 0.0, 0.0)
        controller.position = (0.25, 0.0, 0.0, 0.0, 0.0, 0.0)
        moves = []
        controller.compoundMove = lambda movement, rotation: moves.append((movement, rotation))

        controller.rotateAroundLaser(np.array([0.0, 0.0, 90.0]))

        movement, rotation = moves[0]
        np.testing.assert_allclose(movement, (0.75, -0.75, 0.0), atol=1e-12)
        np.testing.assert_allclose(rotation, (0.0, 0.0, 90.0))

    def test_rotate_around_laser_requires_calibration(self):
        controller = HexapodControl.__new__(HexapodControl)
        controller.laser_position = None

        with self.assertRaisesRegex(ValueError, "has not been calibrated"):
            controller.rotateAroundLaser(np.array([0.0, 0.0, 1.0]))

    def test_manual_rotation_uses_origin_by_default(self):
        tab = HexapodAutomationTab.__new__(HexapodAutomationTab)
        calls = []
        tab.hexapod = SimpleNamespace(
            rotate=lambda rotation: calls.append(("origin", rotation)),
            rotateAroundLaser=lambda rotation: calls.append(("laser", rotation)),
        )
        tab.manualRotationX = FakeValue("1")
        tab.manualRotationY = FakeValue("2")
        tab.manualRotationZ = FakeValue("3")
        tab.rotate_around_laser = FakeValue(False)
        tab.run_hexapod_command = lambda command, **options: command()

        tab.rotate_hexapod()

        self.assertEqual("origin", calls[0][0])
        np.testing.assert_allclose((2, 1, 3), calls[0][1])

    def test_manual_rotation_can_rotate_around_laser(self):
        tab = HexapodAutomationTab.__new__(HexapodAutomationTab)
        calls = []
        tab.hexapod = SimpleNamespace(
            rotate=lambda rotation: calls.append(("origin", rotation)),
            rotateAroundLaser=lambda rotation: calls.append(("laser", rotation)),
        )
        tab.manualRotationX = FakeValue("1")
        tab.manualRotationY = FakeValue("2")
        tab.manualRotationZ = FakeValue("3")
        tab.rotate_around_laser = FakeValue(True)
        tab.run_hexapod_command = lambda command, **options: command()

        tab.rotate_hexapod()

        self.assertEqual("laser", calls[0][0])
        np.testing.assert_allclose((2, 1, 3), calls[0][1])

    def test_infeasible_manual_move_is_shown(self):
        tab = HexapodAutomationTab.__new__(HexapodAutomationTab)
        tab.hexapod = SimpleNamespace(ready_for_commands=True)
        tab.parent = SimpleNamespace(update_idletasks=lambda: None)
        tab.update_command_controls = lambda **options: None
        tab.moveResultLabel = FakeLabel()

        result = tab.run_hexapod_command(
            lambda: "Requested move is not feasible.",
            report_move=True,
        )

        self.assertEqual("Requested move is not feasible.", result)
        self.assertEqual("Last move: Requested move is not feasible.", tab.moveResultLabel.text)
        self.assertEqual("red", tab.moveResultLabel.fg)

    def test_position_display_shows_all_six_axes(self):
        tab = HexapodAutomationTab.__new__(HexapodAutomationTab)
        tab.hexapod = SimpleNamespace(
            position=(1, -2.5, 3.125, 4, 5.5, -6),
            laser_position=None,
        )
        tab.hexapodPositionDisplay = FakeDisplay()
        tab.laserPositionDisplay = FakeDisplay()

        tab.update_position_display()

        self.assertEqual(
            (
                "1.000000",
                "-2.500000",
                "3.125000",
                "4.000000",
                "5.500000",
                "-6.000000",
            ),
            tab.hexapodPositionDisplay.values,
        )
        self.assertIsNone(tab.laserPositionDisplay.values)

    def test_laser_position_shows_face_spot_for_current_pose(self):
        tab = HexapodAutomationTab.__new__(HexapodAutomationTab)
        tab.hexapod = SimpleNamespace(
            position=(10, 20, 30, 0, 0, 0),
            laser_position=(1.5, -2, 0.25),
        )
        tab.hexapodPositionDisplay = FakeDisplay()
        tab.laserPositionDisplay = FakeDisplay()

        tab.update_position_display()

        self.assertEqual(
            ("-8.500000", "-22.000000", "0.250000"),
            tab.laserPositionDisplay.values,
        )


if __name__ == "__main__":
    unittest.main()
