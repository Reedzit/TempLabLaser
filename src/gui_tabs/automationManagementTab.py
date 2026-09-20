import tkinter as tk
import tkinter.filedialog
import src.automationManager as automationManager
from tkinter import ttk
from src.measurementTiming import angle_workflow_seconds, format_duration

class AutomationManagerTab:
    def __init__(self, parent, instruments, main_gui):
        self.parent = parent
        self.main_gui = main_gui
        self.instruments = instruments
        self.manager = automationManager.AutomationManager(self, instruments, None, main_gui)
        self.setup_ui()

    def setup_ui(self):
    # Create main frames
        control_frame = ttk.LabelFrame(self.parent, text="Automation Control")
        control_frame.grid(row=0, column=0, columnspan=4, padx=10, pady=5, sticky='nsew')

        # Automation Control Section
        laser_frame = ttk.LabelFrame(control_frame, text="Laser Control")
        laser_frame.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky='nsew')

        self.startAutomationButton = tk.Button(laser_frame, text="Start Automation", 
                                            command=self.start_automation, state=tk.DISABLED)
        self.startAutomationButton.grid(row=0, column=0, padx=5, pady=5)
        self.measurementEstimate = tk.Label(laser_frame, text="Estimated time: calculating...")
        self.measurementEstimate.grid(row=1, column=0, padx=5, pady=(0, 5), sticky=tk.W)

        focusing_frame = ttk.LabelFrame(control_frame, text="Focusing Control")
        focusing_frame.grid(row=0, column=2, columnspan=2, padx=5, pady=5, sticky='nsew')

        self.startFocussingButton = tk.Button(focusing_frame, text="Start Focussing", 
                                            command=self.runFocussingCycle, state=tk.DISABLED)
        self.startFocussingButton.grid(row=0, column=0, padx=5, pady=5)

        # Configure grid weights
        self.parent.grid_columnconfigure(0, weight=1)
        control_frame.grid_columnconfigure(0, weight=1)
        self.parent.after(0, self.update_measurement_estimate)

    def start_automation(self):
        self.manager.beginAutomation()

    def update_measurement_estimate(self):
        try:
            laser_tab = self.main_gui.laserTabObject
            hexapod_tab = self.main_gui.hexapodTabObject
            sweep_seconds = laser_tab.estimate_frequency_sweep_seconds()
            angle_count = int(hexapod_tab.stepCount.get())
            estimate = angle_workflow_seconds(angle_count, sweep_seconds)
            self.measurementEstimate.configure(
                text=f"Estimated rotation measurement time: {format_duration(estimate)}"
            )
        except (AttributeError, TypeError, ValueError, tk.TclError):
            self.measurementEstimate.configure(
                text="Estimated rotation measurement time: enter valid settings"
            )

    def update_hexapod_command_controls(self, ready):
        raster_tab = getattr(getattr(self, "main_gui", None), "rasteringTabObject", None)
        raster_running = bool(raster_tab and getattr(raster_tab, "scan_running", False))
        state = tk.NORMAL if ready and not raster_running else tk.DISABLED
        self.startAutomationButton.configure(state=state)
        self.startFocussingButton.configure(state=state)

    def runFocussingCycle(self):
        self.manager.runFocussingCycle()
