import datetime
from tkinter import ttk
import tkinter as tk

class AmplifierTab:
    def __init__(self, parent, instruments):
        self.parent = parent
        self.instruments = instruments

        self.setup_ui()

        self.timeConstantDropDown.set(self.instruments.time_constants[5])
        self.update_time_constant()
        self.gainDropDown.set(self.instruments.sensitivities[5])
        self.update_gain()

    def setup_ui(self):
        lockInTab = self.parent
        self.measureBtn = tk.Button(lockInTab, text="Measure", command=self.measure)
        self.measureBtn.pack(padx=10, pady=10)
        self.autoGainBtn = tk.Button(lockInTab, text="Auto Gain", command=self.auto_gain)
        self.autoGainBtn.pack(padx=10, pady=10)
        self.timeConstantLabel = tk.Label(lockInTab, text="Time Constant")
        self.timeConstantLabel.pack(padx=10, pady=5)
        self.timeConstantDropDown = ttk.Combobox(lockInTab,
                                                 values=self.instruments.time_constants)
        self.timeConstantDropDown.pack(padx=10, pady=10)
        self.updateTimeConstantBtn = tk.Button(lockInTab, text="Update Time Constant",
                                               command=self.update_time_constant)
        self.updateTimeConstantBtn.pack(padx=10, pady=10)
        self.increaseTimeConstantBtn = tk.Button(lockInTab, text="Increase Time Constant",
                                                 command=self.increase_time_constant)
        self.increaseTimeConstantBtn.pack(padx=10, pady=10)
        self.decreaseTimeConstantBtn = tk.Button(lockInTab, text="Decrease Time Constant",
                                                 command=self.decrease_time_constant)
        self.decreaseTimeConstantBtn.pack(padx=10, pady=10)
        self.gainLabel = tk.Label(lockInTab, text="Gain")
        self.gainLabel.pack(padx=10, pady=5)
        self.gainDropDown = ttk.Combobox(lockInTab,
                                         values=self.instruments.sensitivities)
        self.gainDropDown.pack(padx=10, pady=10)
        self.updateGainBtn = tk.Button(lockInTab, text="Update Gain", command=self.update_gain)
        self.updateGainBtn.pack(padx=10, pady=10)
        self.increaseGainBtn = tk.Button(lockInTab, text="Increase Gain", command=self.increase_gain)
        self.increaseGainBtn.pack(padx=10, pady=10)
        self.decreaseGainBtn = tk.Button(lockInTab, text="Decrease Gain", command=self.decrease_gain)
        self.decreaseGainBtn.pack(padx=10, pady=10)
        self.lockInTxtBx = tk.Text(lockInTab, height=8, font=('Arial', 16))
        self.lockInTxtBx.pack(padx=10, pady=10)


    def measure(self):
        amplitude, phase = self.instruments.take_measurement()
        self.lockInTxtBx.insert('1.0',
                                f"Time: {datetime.datetime.now().time()} Amplitude: {amplitude} Phase: {phase}\n")

    def auto_gain(self):
        answer = self.instruments.auto_gain()
        self.lockInTxtBx.insert('1.0', f"{answer}\n")

    def update_time_constant(self):
        time_constant = self.timeConstantDropDown.get()
        current = self.instruments.set_time_constant(time_constant)
        self.lockInTxtBx.insert('1.0', f"Time Constant set to: {current}\n")

    def increase_time_constant(self):
        current = self.instruments.increase_time_constant()
        self.timeConstantDropDown.set(current)
        self.update_time_constant()
        # self.lockInTxtBx.insert('1.0', f"Time Constant increased to: {current}\n")

    def decrease_time_constant(self):
        current = self.instruments.decrease_time_constant()
        self.timeConstantDropDown.set(current)
        self.update_time_constant()
        # self.lockInTxtBx.insert('1.0', f"Time Constant decreased to: {current}\n")

    def update_gain(self):
        gain = self.gainDropDown.get()
        current = self.instruments.set_gain(gain)
        self.lockInTxtBx.insert('1.0', f"Gain set to: {current}\n")

    def increase_gain(self):
        current = self.instruments.increase_gain()
        self.gainDropDown.set(current)
        self.update_gain()
        # self.lockInTxtBx.insert('1.0', f"Gain increased to: {current}\n")

    def decrease_gain(self):
        current = self.instruments.decrease_gain()
        self.gainDropDown.set(current)
        self.update_gain()
        # self.lockInTxtBx.insert('1.0', f"Gain decreased to: {current}\n")
