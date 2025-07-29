import tkinter as tk
import tkinter.filedialog
import src.automationManager as automationManager

class AutomationManagerTab:
    def __init__(self, parent, instruments, main_gui):
        self.parent = parent
        self.main_gui = main_gui
        self.instruments = instruments
        self.setup_ui()
        self.manager = automationManager.AutomationManager(self, instruments, None, main_gui)
        self.setup_ui()

    def setup_ui(self):
        self.startAutomationButton = tk.Button(self.parent, text="Start Automation", command=self.start_automation)
        self.startAutomationButton.grid(row=0, column=2, padx=10, pady=10)

        self.stopAutomationButton = tk.Button(self.parent, text="Stop Automation", command=self.stop_automation)
        self.stopAutomationButton.grid(row=0, column=3, padx=10, pady=10)

        self.checkConnectionButton = tk.Button(self.parent, text="Check Connections", command=lambda: self.check_connections(self.parent.laserTabObject, self.parent.hexapodTabObject))
        self.checkConnectionButton.grid(row=0, column=4, padx=10, pady=10)

    def check_connections(self, laserGUI, hexapodGUI):
        self.manager.checkConnections(laserGUI, hexapodGUI)

    def start_automation(self):
        self.manager.beginAutomation()

    def stop_automation(self):
        self.manager.endAutomation()
