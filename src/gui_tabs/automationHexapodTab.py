import tkinter as tk
import tkinter.filedialog
from tkinter import ttk
import ttkbootstrap as ttk
import numpy as np
import threading
from src.hexapod.hexapodControl2 import HexapodControl
from src.hexapod.laserGeometry import laser_spot_on_face
from src.utilities.hexapodCenterFinder.centerFinderGUI import launch_center_finder_popup
import regex as re


class LCDDisplay(tk.Frame):
    def __init__(self, parent, title, axes):
        super().__init__(parent, bg="#101512", bd=2, relief=tk.SUNKEN)
        self.values = []

        tk.Label(
            self,
            text=title,
            bg="#101512",
            fg="#9db6a5",
            font=("TkDefaultFont", 10, "bold"),
        ).grid(row=0, column=0, columnspan=3, padx=8, pady=(6, 2))

        for index, axis in enumerate(axes):
            row = index // 3 + 1
            column = index % 3
            cell = tk.Frame(self, bg="#101512")
            cell.grid(row=row, column=column, padx=8, pady=5, sticky="nsew")
            self.grid_columnconfigure(column, weight=1)

            tk.Label(
                cell,
                text=axis,
                bg="#101512",
                fg="#9db6a5",
                font=("TkDefaultFont", 9),
            ).pack(anchor=tk.W)
            value = tk.StringVar(value="unavailable")
            tk.Label(
                cell,
                textvariable=value,
                bg="#07120b",
                fg="#5cff87",
                font=("Consolas", 14, "bold"),
                width=14,
                anchor=tk.E,
                padx=6,
                pady=3,
                relief=tk.SUNKEN,
                bd=1,
            ).pack(fill=tk.X)
            self.values.append(value)

    def set_values(self, values):
        for variable, value in zip(self.values, values):
            variable.set(value)

    def clear(self):
        for variable in self.values:
            variable.set("unavailable")


class HexapodAutomationTab:
    def __init__(self, parent, instruments, main_gui):
        self.parent = parent
        self.instruments = instruments
        self.main_gui = main_gui
        self.hexapod = None
        self.degrees_of_sweep = tk.StringVar()
        self.stepCount = tk.IntVar(value=20)  # Default step count
        self.hexapodCenter = tk.StringVar(value="0")  # Default center position
        self.pumpLaser = tk.StringVar(value="0")  # Default pump laser state
        self.rotate_around_laser = tk.BooleanVar(value=False)
        self.setup_ui()



    def setup_ui(self):
        # [Previous imports at the top of the file]

        hexapod_automation_tab = self.parent

        # Create main frames
        status_frame = ttk.LabelFrame(hexapod_automation_tab, text="Hexapod Status and Control")
        status_frame.grid(row=0, column=0, columnspan=5, padx=10, pady=5, sticky='nsew')

        movement_frame = ttk.LabelFrame(hexapod_automation_tab, text="Movement Parameters")
        movement_frame.grid(row=1, column=0, columnspan=5, padx=10, pady=5, sticky='nsew')

        adjustment_frame = ttk.LabelFrame(hexapod_automation_tab, text="Manual Adjustment")
        adjustment_frame.grid(row=2, column=0, columnspan=5, padx=10, pady=5, sticky='nsew')

        position_frame = ttk.LabelFrame(hexapod_automation_tab, text="Position Readouts")
        position_frame.grid(row=3, column=0, columnspan=5, padx=10, pady=5, sticky='nsew')

        output_frame = ttk.LabelFrame(hexapod_automation_tab, text="Output and Data")
        output_frame.grid(row=4, column=0, columnspan=5, padx=10, pady=5, sticky='nsew')

        debugging_frame = ttk.LabelFrame(hexapod_automation_tab, text="Debugging Stuff")
        debugging_frame.grid(row=5, column=0, columnspan=5, padx=10, pady=5, sticky='nsew')

        # Status and Control Section
        self.hexapodStatusLabel = tk.Label(status_frame, text="Hexapod Status: Not Connected")
        self.hexapodStatusLabel.grid(row=0, column=0, columnspan=4, padx=10, pady=5)

        self.hexapodPositionDisplay = LCDDisplay(
            position_frame,
            "Hexapod Position",
            ("X (mm)", "Y (mm)", "Z (mm)", "Rx (deg)", "Ry (deg)", "Rz (deg)"),
        )
        self.hexapodPositionDisplay.grid(row=0, column=0, padx=8, pady=8, sticky="nsew")

        self.laserPositionDisplay = LCDDisplay(
            position_frame,
            "Laser Spot on Hexapod Face",
            ("X (mm)", "Y (mm)", "Z (mm)"),
        )
        self.laserPositionDisplay.grid(row=1, column=0, padx=8, pady=8, sticky="nsew")
        position_frame.grid_columnconfigure(0, weight=1)

        self.connectHexapodButton = tk.Button(status_frame, text="Connect to Hexapod",
                                              command=self.connect_hexapod)
        self.connectHexapodButton.grid(row=1, column=0, padx=10, pady=5)

        self.homeHexapodButton = tk.Button(status_frame, text="Home Hexapod",
                                            command=lambda: self.run_hexapod_command(self.hexapod.home),
                                            state=tk.DISABLED)
        self.homeHexapodButton.grid(row=1, column=1, padx=10, pady=5)

        self.controlOnHexapodButton = tk.Button(status_frame, text="Turn on Control (Press this after homing)",
                                                command=lambda: self.run_hexapod_command(self.hexapod.controlOn),
                                                state=tk.DISABLED)
        self.controlOnHexapodButton.grid(row=1, column=2, padx=10, pady=5)

        self.controlOffHexapodButton = tk.Button(status_frame, text="Turn off Control",
                                                 command=lambda: self.run_hexapod_command(self.hexapod.controlOff),
                                                 state=tk.DISABLED)
        self.controlOffHexapodButton.grid(row=1, column=3, padx=10, pady=5)

        self.centerFinderButton = tk.Button(
            status_frame, text="Find Laser Center", command=self.open_center_finder, state=tk.DISABLED
        )
        self.centerFinderButton.grid(row=1, column=4, padx=10, pady=5)

        # Movement Parameters Section
        self.degreesSweepLabel = tk.Label(movement_frame, text="Degrees of Sweep")
        self.degreesSweepLabel.grid(row=0, column=0, padx=10, pady=5, sticky=tk.E)
        self.degreesSweepInput = tk.Entry(movement_frame, textvariable=self.degrees_of_sweep)
        self.degreesSweepInput.grid(row=0, column=1, padx=10, pady=5)

        self.stepCountLabel = tk.Label(movement_frame, text="Step Count:")
        self.stepCount = tk.IntVar(movement_frame, 1)
        self.stepCountInput = tk.Entry(movement_frame, textvariable=self.stepCount, state='normal')
        self.stepCountLabel.grid(row=1, column=0, padx=10, pady=5, sticky=tk.E)
        self.stepCountInput.grid(row=1, column=1, padx=10, pady=5)

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

        # Manual Adjustment Section
        def verify_input(value):
            expression = r"^-?(?:\d+(\.\d*)?|\.\d*)?$"
            if value == "" or re.fullmatch(expression, value):
                return True
            else:
                return False
        vcmd = self.parent.register(verify_input)
                
        self.manualTranslationLabel = tk.Label(adjustment_frame, text="Manual Translation (mm):")
        self.manualTranslationLabel.grid(row=1, column=0, padx=10, pady=5, sticky=tk.E)
        self.manualTranslationX = tk.Entry(adjustment_frame, width=5, validate="all", validatecommand=(vcmd, '%P'))
        self.manualTranslationX.insert(0, "0")
        self.manualTranslationX.grid(row=1, column=1, padx=5, pady=5)
        self.TranslationXLabel = tk.Label(adjustment_frame, text="X")
        self.TranslationXLabel.grid(row=0, column=1, padx=5, pady=5)

        self.manualTranslationY = tk.Entry(adjustment_frame, width=5, validate="all", validatecommand=(vcmd, '%P'))
        self.manualTranslationY.insert(0, "0")
        self.manualTranslationY.grid(row=1, column=2, padx=5, pady=5)
        self.TranslationYLabel = tk.Label(adjustment_frame, text="Y")
        self.TranslationYLabel.grid(row=0, column=2, padx=5, pady=5)


        self.manualTranslationZ = tk.Entry(adjustment_frame, width=5, validate="all", validatecommand=(vcmd, '%P'))
        self.manualTranslationZ.insert(0, "0")
        self.manualTranslationZ.grid(row=1, column=3, padx=5, pady=5)
        self.TranslationZLabel = tk.Label(adjustment_frame, text="Z")
        self.TranslationZLabel.grid(row=0, column=3, padx=5, pady=5)


        self.manualTranslationButton = tk.Button(adjustment_frame, text="Translate",
                                                 command=lambda: self.run_hexapod_command(lambda: self.hexapod.translate(
                                                     np.array([
                                                         float(self.manualTranslationX.get()),
                                                         float(self.manualTranslationY.get()),
                                                         float(self.manualTranslationZ.get())
                                                     ])), report_move=True), state=tk.DISABLED)
        self.manualTranslationButton.grid(row=1, column=4, padx=10, pady=5)
        self.manualTranslationButtonReverse = tk.Button(adjustment_frame, text="Actually go back",
                                                  command=lambda: self.run_hexapod_command(lambda: self.hexapod.translate(
                                                      np.array([
                                                          -float(self.manualTranslationX.get()),
                                                          -float(self.manualTranslationY.get()),
                                                          -float(self.manualTranslationZ.get())
                                                      ])), report_move=True), state=tk.DISABLED)
        self.manualTranslationButtonReverse.grid(row=1, column=5, padx=10, pady=5)
        self.manualRotationLabel = tk.Label(adjustment_frame, text="Rotation (θ°):")
        self.manualRotationLabel.grid(row=2, column=0, padx=10, pady=5, sticky=tk.E)
        self.manualRotationX = tk.Entry(adjustment_frame, width=5)
        self.manualRotationX.grid(row=2, column=1, padx=5, pady=5)

        self.manualRotationY = tk.Entry(adjustment_frame, width=5)
        self.manualRotationY.grid(row=2, column=2, padx=5, pady=5)

        self.manualRotationZ = tk.Entry(adjustment_frame, width=5)
        self.manualRotationZ.grid(row=2, column=3, padx=5, pady=5)

        self.manualRotationButton = tk.Button(
            adjustment_frame,
            text="Rotate",
            command=self.rotate_hexapod,
            state=tk.DISABLED,
        )
        self.manualRotationButton.grid(row=2, column=4, padx=10, pady=5)
        self.rotateAroundLaserCheck = tk.Checkbutton(
            adjustment_frame,
            text="Rotate around laser spot",
            variable=self.rotate_around_laser,
        )
        self.rotateAroundLaserCheck.grid(row=2, column=5, padx=10, pady=5, sticky=tk.W)

        self.moveResultLabel = tk.Label(
            adjustment_frame,
            text="Last move: No move requested",
            anchor=tk.W,
        )
        self.moveResultLabel.grid(row=3, column=0, columnspan=6, padx=10, pady=5, sticky=tk.EW)

        # Debugging Section
        self.printStateButton = tk.Button(debugging_frame, text="Print Hexapod State",
                                          command=self.print_hexapod_state, state=tk.DISABLED)
        self.printStateButton.grid(row=0, column=0, padx=10, pady=5)

        # Configure update timer
        self.hexapodStatusLabel.after(100, self.update_hexapod_status)

        # Configure grid weights
        for frame in (status_frame, movement_frame, output_frame):
            frame.grid_columnconfigure(1, weight=1)

    def print_hexapod_state(self):
        def actually_print():
            if self.hexapod is not None:
                self.hexapod.ready_for_commands = False
                try:
                    print(self.hexapod.getState())
                finally:
                    self.hexapod.checkStatus()
            else:
                print("Hexapod is not connected.")
        if self.hexapod is not None:
            # Run the print in a separate thread to avoid blocking the GUI
            threading.Thread(target=actually_print).start()
        else:
            print("Hexapod is not connected.")

    def select_file_location(self):
        filePath = tk.filedialog.askdirectory()
        if filePath == "":
            return None
        else:
            self.stepFileLocation.set(filePath)
            print(self.stepFileLocation)
            return None

    def connect_hexapod(self):
        self.connectHexapodButton.configure(state=tk.DISABLED)
        self.hexapodStatusLabel.configure(text="Connecting to Hexapod...", fg="black")
        self.parent.update_idletasks()
        try:
            self.hexapod = HexapodControl()
        except Exception as e:
            print(f"Error connecting to Hexapod: {e}")
            self.connectHexapodButton.configure(state=tk.NORMAL)

    def run_hexapod_command(self, command, report_move=False):
        if self.hexapod is None or not getattr(self.hexapod, "ready_for_commands", False):
            return
        self.hexapod.ready_for_commands = False
        self.update_command_controls(connected=True, ready=False)
        self.parent.update_idletasks()
        result = command()
        if report_move:
            if result == "Requested move is not feasible.":
                self.moveResultLabel.configure(
                    text="Last move: Requested move is not feasible.",
                    fg="red",
                )
            elif result == "Success.":
                self.moveResultLabel.configure(text="Last move: Accepted", fg="green")
            else:
                self.moveResultLabel.configure(text=f"Last move: {result}", fg="red")
        return result

    def rotate_hexapod(self):
        rotation = np.array([
            float(self.manualRotationY.get()),
            float(self.manualRotationX.get()),
            float(self.manualRotationZ.get()),
        ])
        if self.rotate_around_laser.get():
            command = lambda: self.hexapod.rotateAroundLaser(rotation)
        else:
            command = lambda: self.hexapod.rotate(rotation)
        self.run_hexapod_command(command, report_move=True)

    def open_center_finder(self):
        launch_center_finder_popup(self.parent.winfo_toplevel(), self.hexapod)

    def update_hexapod_status(self):
        connected = self.hexapod is not None and getattr(self.hexapod, "ssh_API", None) is not None
        ready = connected and getattr(self.hexapod, "ready_for_commands", False)

        if not connected:
            self.hexapodStatusLabel.config(text="Hexapod Not Connected")
        else:
            try:
                self.hexapodStatusLabel.config(
                    text=f"Hexapod Ready for New Commands: {ready}",
                    fg="green" if ready else "red"
                )
            except Exception as e:
                self.hexapodStatusLabel.config(text=f"Error: {e}")

        self.update_position_display()

        self.update_command_controls(connected, ready)

        # update the label every 100 milliseconds
        self.hexapodStatusLabel.after(100, self.update_hexapod_status)

    def update_position_display(self):
        position = getattr(self.hexapod, "position", None)
        if not position or len(position) != 6 or any(value is None for value in position):
            self.hexapodPositionDisplay.clear()
            self.laserPositionDisplay.clear()
            return

        try:
            values = [float(value) for value in position]
        except (TypeError, ValueError):
            self.hexapodPositionDisplay.clear()
            self.laserPositionDisplay.clear()
            return

        x, y, z, rx, ry, rz = values
        self.hexapodPositionDisplay.set_values(
            tuple(f"{value:.6f}" for value in (x, y, z, rx, ry, rz))
        )

        laser_offset = getattr(self.hexapod, "laser_position", None)
        if (
            not laser_offset
            or len(laser_offset) != 3
            or any(value is None for value in laser_offset)
        ):
            self.laserPositionDisplay.clear()
            return

        try:
            laser_spot = laser_spot_on_face(
                laser_offset,
                values,
                getattr(self.hexapod, "calibration_reference_pose", None),
            )
        except (TypeError, ValueError):
            self.laserPositionDisplay.clear()
            return

        self.laserPositionDisplay.set_values(
            tuple(f"{value:.6f}" for value in laser_spot)
        )

    def update_command_controls(self, connected, ready):
        state = tk.NORMAL if ready else tk.DISABLED
        for button in (
            self.homeHexapodButton,
            self.controlOnHexapodButton,
            self.controlOffHexapodButton,
            self.centerFinderButton,
            self.manualTranslationButton,
            self.manualTranslationButtonReverse,
            self.manualRotationButton,
            self.printStateButton,
        ):
            button.configure(state=state)

        self.connectHexapodButton.configure(state=tk.DISABLED if connected else tk.NORMAL)

        for tab_name in ("rasteringTabObject", "cameraControlTabObject", "automationTabObject"):
            tab = getattr(self.main_gui, tab_name, None)
            if tab is not None:
                tab.update_hexapod_command_controls(ready)
