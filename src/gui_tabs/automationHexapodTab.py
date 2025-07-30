import tkinter as tk
import tkinter.filedialog

from src.hexapod.hexapodControl2 import HexapodControl


class HexapodAutomationTab:
    def __init__(self, parent, instruments, main_gui):
        self.parent = parent
        self.instruments = instruments
        self.hexapod = None
        self.degrees_of_sweep = tk.StringVar()
        self.stepCount = tk.IntVar(value=20)  # Default step count
        self.hexapodCenter = tk.StringVar(value="0")  # Default center position
        self.pumpLaser = tk.StringVar(value="0")  # Default pump laser state
        self.setup_ui()



    def setup_ui(self):
        self.hexapodStatusLabel = tk.Label(self.parent, text="Hexapod Status: Not Connected")
        self.hexapodStatusLabel.grid(row=5, column=0, columnspan=4, padx=10, pady=10)

        hexapod_automation_tab = self.parent
        self.connectHexapodButton = tk.Button(hexapod_automation_tab, text="Connect to Hexapod",
                                              command=self.connect_hexapod)
        self.connectHexapodButton.grid(row=6, column=1, columnspan=1, padx=10, pady=10)

        self.homeHexapodButton = tk.Button(hexapod_automation_tab, text="Home Hexapod",
                                            command=lambda: self.hexapod.home())
        self.homeHexapodButton.grid(row=6, column=2, columnspan=1, padx=10, pady=10)

        self.controlOnHexapodButton = tk.Button(hexapod_automation_tab, text="Turn on Control (Press this after homing)",
                                                command=lambda: self.hexapod.control_on())
        self.controlOnHexapodButton.grid(row=6, column=3, columnspan=1, padx=10, pady=10)

        self.controlOffHexapodButton = tk.Button(hexapod_automation_tab, text="Turn off Control",
                                                 command=lambda: self.hexapod.control_off())
        self.controlOffHexapodButton.grid(row=6, column=4, columnspan=1, padx=10, pady=10)

        self.degreesSweepLabel = tk.Label(hexapod_automation_tab, text="Degrees of Sweep")
        self.degreesSweepLabel.grid(row=3, column=0, padx=10, pady=5, sticky=tk.E)
        self.degreesSweepInput = tk.Entry(hexapod_automation_tab, textvariable=self.degrees_of_sweep)
        self.degreesSweepInput.grid(row=3, column=1, padx=10, pady=5)

        self.pumpLaserDistanceLabel = tk.Label(hexapod_automation_tab, text="Distance between lasers (mm)")
        self.pumpLaserDistanceLabel.grid(row=7, column=0, padx=10, pady=10, sticky=tk.E)
        self.pumpLaserDistanceInput = tk.Entry(hexapod_automation_tab)
        self.pumpLaserDistanceInput.insert(0, "1.0")  # Add a default value
        self.pumpLaserDistanceInput.grid(row=7, column=1, padx=10, pady=10)

        self.stepCountLabel = tk.Label(hexapod_automation_tab, text="Step Count:")
        self.stepCount = tk.IntVar(hexapod_automation_tab, 1)
        self.stepCountInput = tk.Entry(hexapod_automation_tab, textvariable=self.stepCount, state='normal')
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

        self.hexapodStatusLabel.after(100, self.update_hexapod_status)

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

    def update_hexapod_status(self):
        if self.hexapod is None:
            self.hexapodStatusLabel.config(text="Hexapod Not Connected")
        else:
            try:
                self.hexapodStatusLabel.config(
                    text=f"Hexapod Ready for New Commands: {self.hexapod.ready_for_commands}",
                    fg="green" if self.hexapod.ready_for_commands else "red"
                )
            except Exception as e:
                self.hexapodStatusLabel.config(text=f"Error: {e}")

        # update the label every 100 milliseconds
        self.hexapodStatusLabel.after(100, self.update_hexapod_status)