import tkinter as tk
import tkinter.filedialog

from src.hexapod.hexapodControl import HexapodControl


class HexapodAutomationTab:
    def __init__(self, parent, instruments):
        self.parent = parent
        self.instruments = instruments
        self.setup_ui()
        self.hexapod = None

    def setup_ui(self):
        hexapod_automation_tab = self.parent
        self.connectHexapodButton = tk.Button(hexapod_automation_tab, text="Connect to Hexapod",
                                              command=self.connect_hexapod)
        self.connectHexapodButton.grid(row=6, column=1, columnspan=1, padx=10, pady=10)

        ### Legacy ###

        self.degreesSweepLabel = tk.Label(hexapod_automation_tab, text="Degrees of Sweep")
        self.degreesSweepLabel.grid(row=3, column=0, padx=10, pady=5, sticky=tk.E)
        self.degreesSweepInput = tk.Entry(hexapod_automation_tab)
        self.degreesSweepInput.grid(row=3, column=1, padx=10, pady=5)

        self.pumpLaserDistanceLabel = tk.Label(hexapod_automation_tab, text="Distance between lasers (mm)")
        self.pumpLaserDistanceLabel.grid(row=7, column=0, padx=10, pady=10, sticky=tk.E)
        self.pumpLaserDistanceInput = tk.Entry(hexapod_automation_tab)
        self.pumpLaserDistanceInput.insert(0, "1.0")  # Add a default value
        self.pumpLaserDistanceInput.grid(row=7, column=1, padx=10, pady=10)

        self.stepCountLabel = tk.Label(hexapod_automation_tab, text="Step Count:")
        self.stepCount = tk.IntVar(hexapod_automation_tab, 1)
        self.stepCountInput = tk.Entry(hexapod_automation_tab, textvariable=self.stepCount, state='disabled')
        self.stepCountInput.grid(row=12, column=1, padx=10, pady=10)
        self.stepCountLabel.grid(row=12, column=0, padx=10, pady=10)

        self.stepFileLocation = tk.StringVar(hexapod_automation_tab, "No Location Given")
        self.stepFileLabel = tk.Label(hexapod_automation_tab, textvariable=self.stepFileLocation)
        self.stepFileButton = tk.Button(hexapod_automation_tab, text="Choose File Location",
                                        command=self.select_file_location)
        self.stepFileLabel.grid(row=10, column=2, columnspan=1, padx=10, pady=10)
        self.stepFileButton.grid(row=10, column=1, padx=10, pady=10)

        self.automationGraph = tk.Label(hexapod_automation_tab)
        self.automationGraph.grid(row=13, column=0, columnspan=4, padx=10, pady=10, sticky='nsew')

    def select_file_location(self):
        filePath = tk.filedialog.askdirectory()
        if filePath == "":
            return None
        else:
            self.stepFileLocation.set(filePath)
            print(self.stepFileLocation)
            return None

    def connect_hexapod(self):
        try:
            self.hexapod = HexapodControl()
            self.hexapod.connectHexapod()
        except Exception as e:
            print(f"Error connecting to Hexapod: {e}")
