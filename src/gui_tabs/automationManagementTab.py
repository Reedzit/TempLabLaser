import tkinter as tk
import tkinter.filedialog
import src.automationManager as automationManager
from tkinter import ttk

class AutomationManagerTab:
    def __init__(self, parent, instruments, main_gui):
        self.parent = parent
        self.main_gui = main_gui
        self.instruments = instruments
        self.setup_ui()
        self.manager = automationManager.AutomationManager(self, instruments, None, main_gui)
        self.setup_ui()

    def setup_ui(self):
    # Create main frames
        control_frame = ttk.LabelFrame(self.parent, text="Automation Control")
        control_frame.grid(row=0, column=0, columnspan=6, padx=10, pady=5, sticky='nsew')

        status_frame = ttk.LabelFrame(self.parent, text="Automation Status")
        status_frame.grid(row=1, column=0, columnspan=6, padx=10, pady=5, sticky='nsew')

        # Automation Control Section
        laser_frame = ttk.LabelFrame(control_frame, text="Laser Control")
        laser_frame.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky='nsew')

        self.startAutomationButton = tk.Button(laser_frame, text="Start Automation", 
                                            command=self.start_automation)
        self.startAutomationButton.grid(row=0, column=0, padx=5, pady=5)

        self.stopAutomationButton = tk.Button(laser_frame, text="Stop Automation", 
                                            command=self.stop_automation)
        self.stopAutomationButton.grid(row=0, column=1, padx=5, pady=5)

        focusing_frame = ttk.LabelFrame(control_frame, text="Focusing Control")
        focusing_frame.grid(row=0, column=2, columnspan=2, padx=5, pady=5, sticky='nsew')

        self.startFocussingButton = tk.Button(focusing_frame, text="Start Focussing", 
                                            command=self.runFocussingCycle)
        self.startFocussingButton.grid(row=0, column=0, padx=5, pady=5)

        self.stopFocussingButton = tk.Button(focusing_frame, text="Stop Focussing", 
                                        command=self.endFocussing)
        self.stopFocussingButton.grid(row=0, column=1, padx=5, pady=5)

        system_frame = ttk.LabelFrame(control_frame, text="System Control")
        system_frame.grid(row=0, column=4, columnspan=2, padx=5, pady=5, sticky='nsew')

        self.checkConnectionButton = tk.Button(system_frame, text="Check Connections", 
                                            command=lambda: self.check_connections(
                                                self.parent.laserTabObject, 
                                                self.parent.hexapodTabObject))
        self.checkConnectionButton.grid(row=0, column=0, padx=5, pady=5)

        # Status Section
        progress_label = ttk.Label(status_frame, text="Automation Progress:")
        progress_label.grid(row=0, column=0, padx=5, pady=2, sticky='w')

        self.progress_bar = ttk.Progressbar(status_frame, orient="horizontal", 
                                        length=300, mode="determinate")
        self.progress_bar.grid(row=1, column=0, columnspan=6, padx=5, pady=2, sticky='ew')
        
        # Set initial progress value to 50%
        self.progress_bar['value'] = 50

        # Configure grid weights
        self.parent.grid_columnconfigure(0, weight=1)
        for frame in (control_frame, status_frame):
            frame.grid_columnconfigure(0, weight=1)
        
        # 



    def check_connections(self, laserGUI, hexapodGUI):
        self.manager.checkConnections(laserGUI, hexapodGUI)

    def start_automation(self):
        self.manager.beginAutomation()

    def stop_automation(self):
        self.manager.endAutomation()
    
    def runFocussingCycle(self):
        self.manager.runFocussingCycle()

    def endFocussing(self):
        self.manager.endFocussing()