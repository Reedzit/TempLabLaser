import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from instrumentInitialize import InstrumentInitialize
from instrument_configurations.fgConfig import fgConfig
from hexapod.hexapodControl import HexapodControl
import json
import os
# import pymeasure.instruments.srs.sr830 as lia

class MicroscopeGUI():

    CONFIG_FILE = "src\\instrument_configurations\\configs.json"
    instruments = InstrumentInitialize()
    hexapod = None

    def __init__(self):
        self.load_configs()

        window = tk.Tk()
        window.geometry("1000x1000")
        window.title("Microscope GUI")
        notebook = ttk.Notebook(window)
        instrumentsTab = tk.Frame(notebook)
        hexapodTab = tk.Frame(notebook)
        lockInTab = tk.Frame(notebook)
        notebook.add(instrumentsTab, text='Instruments')
        notebook.add(hexapodTab, text='Hexapod')
        notebook.add(lockInTab, text='Lock In Amplifier')
        notebook.pack(expand=1, fill='both')

        ### Instruments Tab ###
        self.configDropdown = ttk.Combobox(instrumentsTab, textvariable="Select a configuration", values=self.instruments.fgConfigNames)
        self.configDropdown.grid(row=0, column=1, padx=10, pady=10)
        self.updateConfigButton = tk.Button(instrumentsTab, text="Update Configuration", command=self.update_config)
        self.updateConfigButton.grid(row=0, column=2, padx=10, pady=10)

        self.deleteConfigBtn = tk.Button(instrumentsTab, text="Delete Configuration", command=self.delete_config)
        self.deleteConfigBtn.grid(row=0, column=3, padx=10, pady=10)

        self.createConfigLabel = tk.Label(instrumentsTab, text="Create Configuration")
        self.createConfigLabel.grid(row=1, column=0, columnspan=3, padx=10, pady=10)

        self.configNameLabel = tk.Label(instrumentsTab, text="Configuration Name")
        self.configNameLabel.grid(row=2, column=0, padx=10, pady=10, sticky=tk.E)
        self.configNameInput = tk.Entry(instrumentsTab, text="Name")
        self.configNameInput.grid(row=2, column=1, padx=10, pady=10)

        self.freqLabel = tk.Label(instrumentsTab, text="Frequency (Hz)")
        self.freqLabel.grid(row=3, column=0, padx=10, pady=10, sticky=tk.E)
        self.freqInput = tk.Entry(instrumentsTab, text="Frequency")
        self.freqInput.grid(row=3, column=1, padx=10, pady=10)

        self.ampLabel = tk.Label(instrumentsTab, text="Amplitude (V)")
        self.ampLabel.grid(row=4, column=0, padx=10, pady=10, sticky=tk.E)
        self.ampInput = tk.Entry(instrumentsTab, text="Amplitude")
        self.ampInput.grid(row=4, column=1, padx=10, pady=10)

        self.offsetLabel = tk.Label(instrumentsTab, text="Offset (V)")
        self.offsetLabel.grid(row=5, column=0, padx=10, pady=10, sticky=tk.E)
        self.offsetInput = tk.Entry(instrumentsTab, text="Offset")
        self.offsetInput.grid(row=5, column=1, padx=10, pady=10)

        self.createConfigButton = tk.Button(instrumentsTab, text="Create Configuration", command=self.create_config)
        self.createConfigButton.grid(row=6, column=0, columnspan=3, padx=10, pady=10)

        self.phaseLabel = tk.Label(instrumentsTab, text="Adjust Channel 2 Phase (degrees)")
        self.phaseLabel.grid(row=7, column=0, padx=10, pady=10, sticky=tk.E)
        self.phaseInput = tk.Entry(instrumentsTab, text="Phase")
        self.phaseInput.grid(row=7, column=1, padx=10, pady=10)
        self.setPhaseBtn = tk.Button(instrumentsTab, text="Set Phase", command=self.set_phase)
        self.setPhaseBtn.grid(row=7, column=2, padx=10, pady=10)

        self.instrumentsTxtBx = tk.Text(instrumentsTab, height=8,  font=('Arial', 16))
        self.instrumentsTxtBx.grid(row=8, column=0, columnspan=4, padx=10, pady=10)
        
        
        
        ### Hexapod Tab ###
        self.connectBtn = tk.Button(hexapodTab, text="Connect to Hexapod", command=self.connect_hexapod)
        self.connectBtn.pack(padx=10, pady=10)
        self.homeBtn = tk.Button(hexapodTab, text="Home Hexapod", command=self.home_hexapod)
        self.homeBtn.pack(padx=10, pady=10)
        self.controlOnBtn = tk.Button(hexapodTab, text="Turn on Control (Press this after homing)", command=self.control_on_hexapod)
        self.controlOnBtn.pack(padx=10, pady=10)
        self.stepLabel = tk.Label(hexapodTab, text="Step Size (mm)")
        self.stepLabel.pack(padx=10, pady=5)
        self.stepInput = tk.Entry(hexapodTab, text="Step Size")
        self.stepInput.pack(padx=10, pady=10)
        self.resetBtn = tk.Button(hexapodTab, text="Reset Position", command=self.reset_position)
        self.resetBtn.pack(padx=10, pady=10)
    

        bfTranslation = tk.Frame(hexapodTab)
        bfTranslation.columnconfigure(0, weight=1)
        bfTranslation.columnconfigure(1, weight=1)
        bfTranslation.columnconfigure(2, weight=1)
        bfTranslation.rowconfigure(0, weight=1)
        bfTranslation.rowconfigure(1, weight=1)
        bfTranslation.rowconfigure(2, weight=1)

        btn_up = tk.Button(bfTranslation, text="Up", command=self.move_up, font=('Arial', 18))
        btn_up.grid(row=0, column=1, sticky=tk.W+tk.E)

        btn_left = tk.Button(bfTranslation, text="Left", command=self.move_left, font=('Arial', 18))
        btn_left.grid(row=1, column=0, sticky=tk.W+tk.E)

        btn_down = tk.Button(bfTranslation, text="Down", command=self.move_down, font=('Arial', 18))
        btn_down.grid(row=1, column=1, sticky=tk.W+tk.E)

        btn_right = tk.Button(bfTranslation, text="Right", command=self.move_right, font=('Arial', 18))
        btn_right.grid(row=1, column=2, sticky=tk.W+tk.E)

        btn_in = tk.Button(bfTranslation, text="In", command=self.move_in, font=('Arial', 18))
        btn_in.grid(row=2, column=1, sticky=tk.W+tk.E)

        btn_out = tk.Button(bfTranslation, text="Out", command=self.move_out, font=('Arial', 18))
        btn_out.grid(row=3, column=1, sticky=tk.W+tk.E)

        bfTranslation.pack(fill='x', padx=20, pady=20)

        self.hexapodTextbox = tk.Text(hexapodTab, height=8,  font=('Arial', 16))
        self.hexapodTextbox.pack(padx=10, pady=10, side=tk.BOTTOM, fill=tk.X)

        ### Lock In Amplifier Tab ###
        self.measureBtn = tk.Button(lockInTab, text="Measure", command=self.measure)
        self.measureBtn.pack(padx=10, pady=10)
        self.autoGainBtn = tk.Button(lockInTab, text="Auto Gain", command=self.auto_gain)
        self.autoGainBtn.pack(padx=10, pady=10)
        self.timeConstantLabel = tk.Label(lockInTab, text="Time Constant")
        self.timeConstantLabel.pack(padx=10, pady=5)
        self.timeConstantDropDown = ttk.Combobox(lockInTab, textvariable="Select a time constant", values=self.instruments.time_constants)
        self.timeConstantDropDown.pack(padx=10, pady=10)
        self.updateTimeConstantBtn = tk.Button(lockInTab, text="Update Time Constant", command=self.update_time_constant)
        self.updateTimeConstantBtn.pack(padx=10, pady=10)
        self.increaseTimeConstantBtn = tk.Button(lockInTab, text="Increase Time Constant", command=self.increase_time_constant)
        self.increaseTimeConstantBtn.pack(padx=10, pady=10)
        self.decreaseTimeConstantBtn = tk.Button(lockInTab, text="Decrease Time Constant", command=self.decrease_time_constant)
        self.decreaseTimeConstantBtn.pack(padx=10, pady=10)
        self.gainLabel = tk.Label(lockInTab, text="Gain")
        self.gainLabel.pack(padx=10, pady=5)
        self.gainDropDown = ttk.Combobox(lockInTab, textvariable="Select a gain Value", values=self.instruments.sensitivities)
        self.gainDropDown.pack(padx=10, pady=10)
        self.updateGainBtn = tk.Button(lockInTab, text="Update Gain", command=self.update_gain)
        self.updateGainBtn.pack(padx=10, pady=10)
        self.increaseGainBtn = tk.Button(lockInTab, text="Increase Gain", command=self.increase_gain)
        self.increaseGainBtn.pack(padx=10, pady=10)
        self.decreaseGainBtn = tk.Button(lockInTab, text="Decrease Gain", command=self.decrease_gain)
        self.decreaseGainBtn.pack(padx=10, pady=10)
        self.lockInTxtBx = tk.Text(lockInTab, height=8,  font=('Arial', 16))
        self.lockInTxtBx.pack(padx=10, pady=10)

        # initialize
        self.timeConstantDropDown.set(self.instruments.time_constants[5])
        self.update_time_constant()
        self.gainDropDown.set(self.instruments.sensitivities[5])
        self.update_gain()

        window.mainloop()

    def measure(self):
        amplitude, phase = self.instruments.take_measurement()
        import datetime
        
        self.lockInTxtBx.insert('1.0', f"Time: {datetime.datetime.now().time()} Amplitude: {amplitude} Phase: {phase}\n")
    
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

    def load_configs(self):
        configurations = {}
        if os.path.exists(self.CONFIG_FILE):
            with open(self.CONFIG_FILE, 'r') as f:
                data = json.load(f)
                for name, config in data.items():
                    current = fgConfig(name=config['name'], 
                                                    frequency=float(config['frequency']),
                                                    amplitude=float(config['amplitude']),
                                                    offset=float(config['offset']))
                    self.instruments.FgConfigs[name] = current
                    configurations[name] = current
                    self.instruments.fgConfigNames.append(name)
        return configurations

    def save_configurations(self):
        with open(self.CONFIG_FILE, 'w') as file:
            json.dump({name: config.to_dict() for name, config in self.instruments.FgConfigs.items()}, file, indent=4)

    def update_config(self):
        configName = self.configDropdown.get()
        self.instruments.set_current_fg_config(configName)
        self.instruments.update_configuration()
        self.instrumentsTxtBx.insert(tk.END, "Updated configuration to " + configName + "\n")
        self.instrumentsTxtBx.insert(tk.END, f"Frequency: {self.instruments.current_fg_config.frequency}\nAmplitude: {self.instruments.current_fg_config.amplitude}\nOffset: {self.instruments.current_fg_config.offset}\n\n")

    def create_config(self):
        config_name = self.configNameInput.get()
        freq = self.freqInput.get()
        amp = self.ampInput.get()
        offset = self.offsetInput.get()
        self.instruments.create_fg_config(config_name, freq, amp, offset)
        self.save_configurations()
        self.configDropdown['values'] = list(self.instruments.FgConfigs.keys())
        self.configDropdown.set('')  # Clear the current selection
        self.instrumentsTxtBx.insert(tk.END, "Created configuration " + config_name + "\n")

    def delete_config(self):
        configName = self.configDropdown.get()
        self.instruments.delete_fg_config(configName)
        self.save_configurations()
        self.instrumentsTxtBx.insert(tk.END, "Deleted configuration " + configName + "\n")
        self.configDropdown['values'] = list(self.instruments.FgConfigs.keys())

    def set_phase(self):
        phase = self.phaseInput.get()
        value = self.instruments.set_phase(phase)
        self.instrumentsTxtBx.insert(tk.END, "Channel 2 phase set to " + str(value) + "\n")

    def connect_hexapod(self):
        try:
            self.hexapod = HexapodControl()
        except Exception as e:
            self.hexapodTextbox.insert(tk.END, "Unable to connect to hexapod.\n Error: " + str(e) + "\n")

    def home_hexapod(self):
        if self.hexapod is None or not self.hexapod.ssh_API:
            print("Not connected to hexapod")
        else:
            response = self.hexapod.home()
            self.hexapodTextbox.insert(tk.END, f"Home: {response}\n")

    def control_on_hexapod(self):
        if self.hexapod is None or not self.hexapod.ssh_API:
            print("Not connected to hexapod")
        else:
            response = self.hexapod.controlOn()
            self.hexapodTextbox.insert(tk.END, f"Control on: {response}\n")

    def move_up(self):
        if self.hexapod is None or not self.hexapod.ssh_API:
            print("Not connected to hexapod")
        else:
            response = self.hexapod.moveUp(self.stepInput.get())
            self.hexapodTextbox.insert(tk.END, f"Move up: {response}\n")

    def move_down(self):
        if self.hexapod is None or not self.hexapod.ssh_API:
            print("Move Down")
        else:
            response = self.hexapod.moveDown(self.stepInput.get())
            self.hexapodTextbox.insert(tk.END, f"Move down: {response}\n")

    def move_left(self):
        if self.hexapod is None or not self.hexapod.ssh_API:
            print("Move Left")
        else:
            response = self.hexapod.moveLeft(self.stepInput.get())
            self.hexapodTextbox.insert(tk.END, f"Move left: {response}\n")

    def move_right(self):
        if self.hexapod is None or not self.hexapod.ssh_API:
            print("Move Right")
        else:
            response = self.hexapod.moveRight(self.stepInput.get())
            self.hexapodTextbox.insert(tk.END, f"Move right: {response}\n")

    def move_in(self):
        if self.hexapod is None or not self.hexapod.ssh_API:
            print("Move In")
        else:
            response = self.hexapod.moveIn(self.stepInput.get())
            self.hexapodTextbox.insert(tk.END, f"Move in: {response}\n")

    def move_out(self):
        if self.hexapod is None or not self.hexapod.ssh_API:
            print("Move Out")
        else:
            response = self.hexapod.moveOut(self.stepInput.get())
            self.hexapodTextbox.insert(tk.END, f"Move out: {response}\n")

    def reset_position(self):
        if self.hexapod is None or not self.hexapod.ssh_API:
            print("Reset Position")
        else:
            response = self.hexapod.resetPosition()
            self.hexapodTextbox.insert(tk.END, f"Reset Position: {response}\n")


if __name__ == '__main__':
    MicroscopeGUI()