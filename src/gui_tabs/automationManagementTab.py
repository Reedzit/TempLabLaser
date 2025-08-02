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
        self.automation_progress = 0

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
        self.progress_label = ttk.Label(status_frame, text="Automation Progress: 0.0%")
        self.progress_label.grid(row=0, column=0, padx=5, pady=2, sticky='w')

        self.progress_bar = ttk.Progressbar(status_frame, orient="horizontal", 
                                        length=300, mode="determinate")
        self.progress_bar.grid(row=1, column=0, columnspan=6, padx=5, pady=2, sticky='ew')
        
        # Set initial progress value to 50%
        self.progress_bar['value'] = 50

        # Configure grid weights
        self.parent.grid_columnconfigure(0, weight=1)
        for frame in (control_frame, status_frame):
            frame.grid_columnconfigure(0, weight=1)
        

    def update_progress(self):
        """
        Updates the progress bar and schedules the next update.
        Called every 100ms to update the progress display.
        """
        # Add progress value update logic here
        try:
            # The progress value should be between 0 and 100
            current_progress = self.automation_progress
            self.progress_bar['value'] = current_progress

            # Update progress label with percentage
            progress_text = f"Automation Progress: {current_progress:.1f}%"
            self.progress_label.configure(text=progress_text)

        except Exception as e:
            print(f"Error updating progress: {e}")

        # Schedule next update in 100ms
        self.parent.after(100, self.update_progress)

    def start_progress_updates(self):
        """
        Starts the progress update loop
        """
        self.update_progress()

    def stop_progress_updates(self):
        """
        Resets the progress bar to 0
        """
        self.progress_bar['value'] = 0
        self.progress_label.configure(text="Automation Progress: 0.0%")


    def check_connections(self, laserGUI, hexapodGUI):
        self.manager.checkConnections(laserGUI, hexapodGUI)

    def start_automation(self):
        self.manager.beginAutomation()
        self.start_progress_updates()

    def stop_automation(self):
        self.manager.endAutomation()
        self.stop_progress_updates()
    
    def runFocussingCycle(self):
        self.manager.runFocussingCycle()

    def endFocussing(self):
        self.manager.endFocussing()