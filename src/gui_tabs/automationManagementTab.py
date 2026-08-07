import tkinter as tk
import tkinter.filedialog
import src.automationManager as automationManager
from tkinter import ttk

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

        focusing_frame = ttk.LabelFrame(control_frame, text="Focusing Control")
        focusing_frame.grid(row=0, column=2, columnspan=2, padx=5, pady=5, sticky='nsew')

        self.startFocussingButton = tk.Button(focusing_frame, text="Start Focussing", 
                                            command=self.runFocussingCycle, state=tk.DISABLED)
        self.startFocussingButton.grid(row=0, column=0, padx=5, pady=5)

        # Configure grid weights
        self.parent.grid_columnconfigure(0, weight=1)
        control_frame.grid_columnconfigure(0, weight=1)

    def start_automation(self):
        self.manager.beginAutomation()

    def update_hexapod_command_controls(self, ready):
        state = tk.NORMAL if ready else tk.DISABLED
        self.startAutomationButton.configure(state=state)
        self.startFocussingButton.configure(state=state)

    def runFocussingCycle(self):
        self.manager.runFocussingCycle()
