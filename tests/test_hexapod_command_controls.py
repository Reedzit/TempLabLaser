import unittest
from types import SimpleNamespace

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

    def config(self, **options):
        self.text = options.get("text", self.text)


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

    def test_position_display_shows_all_six_axes(self):
        tab = HexapodAutomationTab.__new__(HexapodAutomationTab)
        tab.hexapod = SimpleNamespace(position=(1, -2.5, 3.125, 4, 5.5, -6))
        tab.hexapodPositionLabel = FakeLabel()

        tab.update_position_display()

        self.assertEqual(
            "Position (mm): X 1.000, Y -2.500, Z 3.125\n"
            "Rotation (deg): Rx 4.000, Ry 5.500, Rz -6.000",
            tab.hexapodPositionLabel.text,
        )


if __name__ == "__main__":
    unittest.main()
