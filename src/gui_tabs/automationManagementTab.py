import tkinter as tk
import tkinter.filedialog


class AutomationManagerTab:
    def __init__(self, parent, instruments):
        self.parent = parent
        self.instruments = instruments
        self.setup_ui()

    def setup_ui(self):
        self.startAutomationButton = tk.Button(self.parent, text="Start Automation", command=self.start_automation)
        self.startAutomationButton.pack(padx=10, pady=10)

        self.stopAutomationButton = tk.Button(self.parent, text="Stop Automation", command=self.stop_automation)
        self.stopAutomationButton.pack(padx=10, pady=10)

    def start_automation(self):
        self.instruments.start_automation()

    def stop_automation(self):
        self.instruments.stop_automation()
