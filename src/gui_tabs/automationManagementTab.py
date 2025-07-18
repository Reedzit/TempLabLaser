import tkinter as tk
import tkinter.filedialog
import src.automationManager as automationManager

class AutomationManagerTab:
    def __init__(self, parent, instruments):
        self.parent = parent
        self.instruments = instruments
        self.setup_ui()
        self.manager = automationManager.AutomationManager(self, instruments, None)
        self.setup_ui()

    def setup_ui(self):
        self.startAutomationButton = tk.Button(self.parent, text="Start Automation", command=self.start_automation)
        self.startAutomationButton.grid(row=0, column=2, padx=10, pady=10)

        self.stopAutomationButton = tk.Button(self.parent, text="Stop Automation", command=self.stop_automation)
        self.stopAutomationButton.grid(row=0, column=3, padx=10, pady=10)

    def start_automation(self):
        self.manager.runAutomationCycle()

    def stop_automation(self):
        self.manager.endAutomation()
