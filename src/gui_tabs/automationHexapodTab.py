import tkinter as tk
import tkinter.filedialog
from tkinter import ttk
import ttkbootstrap as ttk

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
        # [Previous imports at the top of the file]

        hexapod_automation_tab = self.parent

        # Create main frames
        status_frame = ttk.LabelFrame(hexapod_automation_tab, text="Hexapod Status and Control")
        status_frame.grid(row=0, column=0, columnspan=5, padx=10, pady=5, sticky='nsew')

        movement_frame = ttk.LabelFrame(hexapod_automation_tab, text="Movement Parameters")
        movement_frame.grid(row=1, column=0, columnspan=5, padx=10, pady=5, sticky='nsew')

        output_frame = ttk.LabelFrame(hexapod_automation_tab, text="Output and Data")
        output_frame.grid(row=2, column=0, columnspan=5, padx=10, pady=5, sticky='nsew')

        # Add new constraints frame
        constraints_frame = ttk.LabelFrame(hexapod_automation_tab, text="Movement Constraints")
        constraints_frame.grid(row=2, column=0, columnspan=5, padx=10, pady=5, sticky='nsew')

        # Create a subframe for the meters to control their size and layout
        meters_frame = ttk.Frame(constraints_frame)
        meters_frame.grid(row=0, column=0, columnspan=6, padx=5, pady=5)

        # Define coordinate systems with their ranges
        coordinates = {
            'X': {'name': 'X Position', 'range': (-30, 30)},  # ±50mm
            'Y': {'name': 'Y Position', 'range': (-30, 30)},  # ±50mm
            'Z': {'name': 'Z Position', 'range': (-20, 20)},  # ±25mm
            'Roll (Rx)': {'name': 'Roll', 'range': (-11, 11)},     # ±20°
            'Pitch (Ry)': {'name': 'Pitch', 'range': (-11, 11)},   # ±20°
            'Yaw (Rz)': {'name': 'Yaw', 'range': (-20, 20)}        # ±20°
        }

        self.constraint_meters = {}

        for i, (coord, info) in enumerate(coordinates.items()):
            # Create frame for each meter
            meter_frame = ttk.LabelFrame(meters_frame, text=info['name'])
            meter_frame.grid(row=i//3, column=i%3, padx=5, pady=5)

            # Create meter with small size
            meter = ttk.Meter(
                meter_frame,
                metersize=150,
                padding=5,
                amountused=50,  # Start at middle position
                metertype="full",  # Full circle display
                subtext=f"Range: {info['range'][0]} to {info['range'][1]}",
                interactive=False,
                stripethickness=10
            )
            meter.pack(padx=5, pady=5)

            # Store meter reference
            self.constraint_meters[coord] = {
                'meter': meter,
                'range': info['range']
            }

        # Method to update meter values

        # Status and Control Section
        self.hexapodStatusLabel = tk.Label(status_frame, text="Hexapod Status: Not Connected")
        self.hexapodStatusLabel.grid(row=0, column=0, columnspan=4, padx=10, pady=5)

        self.connectHexapodButton = tk.Button(status_frame, text="Connect to Hexapod",
                                              command=self.connect_hexapod)
        self.connectHexapodButton.grid(row=1, column=0, padx=10, pady=5)

        self.homeHexapodButton = tk.Button(status_frame, text="Home Hexapod",
                                            command=lambda: self.hexapod.home())
        self.homeHexapodButton.grid(row=1, column=1, padx=10, pady=5)

        self.controlOnHexapodButton = tk.Button(status_frame, text="Turn on Control (Press this after homing)",
                                                command=lambda: self.hexapod.control_on())
        self.controlOnHexapodButton.grid(row=1, column=2, padx=10, pady=5)

        self.controlOffHexapodButton = tk.Button(status_frame, text="Turn off Control",
                                                 command=lambda: self.hexapod.control_off())
        self.controlOffHexapodButton.grid(row=1, column=3, padx=10, pady=5)

        # Movement Parameters Section
        self.degreesSweepLabel = tk.Label(movement_frame, text="Degrees of Sweep")
        self.degreesSweepLabel.grid(row=0, column=0, padx=10, pady=5, sticky=tk.E)
        self.degreesSweepInput = tk.Entry(movement_frame, textvariable=self.degrees_of_sweep)
        self.degreesSweepInput.grid(row=0, column=1, padx=10, pady=5)

        self.pumpLaserDistanceLabel = tk.Label(movement_frame, text="Distance between lasers (mm)")
        self.pumpLaserDistanceLabel.grid(row=1, column=0, padx=10, pady=5, sticky=tk.E)
        self.pumpLaserDistanceInput = tk.Entry(movement_frame)
        self.pumpLaserDistanceInput.insert(0, "1.0")
        self.pumpLaserDistanceInput.grid(row=1, column=1, padx=10, pady=5)

        self.stepCountLabel = tk.Label(movement_frame, text="Step Count:")
        self.stepCount = tk.IntVar(movement_frame, 1)
        self.stepCountInput = tk.Entry(movement_frame, textvariable=self.stepCount, state='normal')
        self.stepCountLabel.grid(row=2, column=0, padx=10, pady=5, sticky=tk.E)
        self.stepCountInput.grid(row=2, column=1, padx=10, pady=5)

        # Output and Data Section
        file_frame = ttk.Frame(output_frame)
        file_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=5)

        self.stepFileLocation = tk.StringVar(file_frame, "No Location Given")
        self.stepFileButton = tk.Button(file_frame, text="Choose File Location",
                                        command=self.select_file_location)
        self.stepFileButton.grid(row=0, column=0, padx=10, pady=5)
        
        self.stepFileLabel = tk.Label(file_frame, textvariable=self.stepFileLocation)
        self.stepFileLabel.grid(row=0, column=1, padx=10, pady=5)

        self.automationGraph = tk.Label(output_frame)
        self.automationGraph.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky='nsew')

        # Configure update timer
        self.hexapodStatusLabel.after(100, self.update_hexapod_status)

        # Configure grid weights
        for frame in (status_frame, movement_frame, output_frame):
            frame.grid_columnconfigure(1, weight=1)

    def update_meter_value(self, coordinate, pos_constraint, neg_constraint):
        """
        Update meter to show constraints in both positive and negative directions

        Args:
            coordinate: The coordinate to update ('X', 'Y', etc.)
            pos_constraint: Constraint in positive direction (0-100%)
            neg_constraint: Constraint in negative direction (0-100%)
        """
        meter = self.constraint_meters[coordinate]['meter']
        total_range = abs(self.constraint_meters[coordinate]['range'][1] -
                          self.constraint_meters[coordinate]['range'][0])

        # Calculate the amount used based on constraints
        pos_amount = (100 - pos_constraint) * (total_range / 2) / 100
        neg_amount = (100 - neg_constraint) * (total_range / 2) / 100

        # Update meter display
        meter.configure(
            amountused=(pos_amount + neg_amount) / total_range * 100,
            sublabel=f"+{pos_amount:.1f}/-{neg_amount:.1f}"
        )

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