import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from instrumentInitialize import InstrumentInitialize
from instrument_configurations.fgConfig import fgConfig
from hexapod.hexapodControl import HexapodControl
import json
import os
import pymeasure.instruments.srs.sr830 as lia

class MicroscopeGUI():

    CONFIG_FILE = "instrument_configurations\\configs.json"
    instruments = InstrumentInitialize()
    hexapod = None

    def __init__(self):
        self.configurations = self.load_configs()

        window = tk.Tk()
        window.geometry("800x800")
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

        self.createConfigLabel = tk.Label(instrumentsTab, text="Create Configuration")
        self.createConfigLabel.grid(row=1, column=0, columnspan=3, padx=10, pady=10)

        self.configNameLabel = tk.Label(instrumentsTab, text="Configuration Name")
        self.configNameLabel.grid(row=2, column=0, padx=10, pady=10, sticky=tk.E)
        self.configNameInput = tk.Entry(instrumentsTab, text="Name")
        self.configNameInput.grid(row=2, column=1, padx=10, pady=10)

        self.freqLabel = tk.Label(instrumentsTab, text="Frequency")
        self.freqLabel.grid(row=3, column=0, padx=10, pady=10, sticky=tk.E)
        self.freqInput = tk.Entry(instrumentsTab, text="Frequency")
        self.freqInput.grid(row=3, column=1, padx=10, pady=10)

        self.ampLabel = tk.Label(instrumentsTab, text="Amplitude")
        self.ampLabel.grid(row=4, column=0, padx=10, pady=10, sticky=tk.E)
        self.ampInput = tk.Entry(instrumentsTab, text="Amplitude")
        self.ampInput.grid(row=4, column=1, padx=10, pady=10)

        self.offsetLabel = tk.Label(instrumentsTab, text="Offset")
        self.offsetLabel.grid(row=5, column=0, padx=10, pady=10, sticky=tk.E)
        self.offsetInput = tk.Entry(instrumentsTab, text="Offset")
        self.offsetInput.grid(row=5, column=1, padx=10, pady=10)

        self.createConfigButton = tk.Button(instrumentsTab, text="Create Configuration", command=self.create_config)
        self.createConfigButton.grid(row=6, column=0, columnspan=3, padx=10, pady=10)

        self.instrumentsTxtBx = tk.Text(instrumentsTab, height=8,  font=('Arial', 16))
        self.instrumentsTxtBx.grid(row=8, column=0, columnspan=4, padx=10, pady=10)
        
        
        
        ### Hexapod Tab ###
        self.connectBtn = tk.Button(hexapodTab, text="Connect to Hexapod", command=self.connect_hexapod)
        self.connectBtn.pack(padx=10, pady=10)
        self.homeBtn = tk.Button(hexapodTab, text="Home Hexapod", command=self.home_hexapod)
        self.homeBtn.pack(padx=10, pady=10)
        self.controlOnBtn = tk.Button(hexapodTab, text="Turn on Control", command=self.control_on_hexapod)
        self.controlOnBtn.pack(padx=10, pady=10)
        self.stepLabel = tk.Label(hexapodTab, text="Step Size (mm)")
        self.stepLabel.pack(padx=10, pady=5)
        self.stepInput = tk.Entry(hexapodTab, text="Step Size")
        self.stepInput.pack(padx=10, pady=10)
        #TODO: add speed feature
        # self.speedLabel = tk.Label(hexapodTab, text="Speed")
        # self.speedLabel.pack(padx=10, pady=5)
        # self.speedInput = tk.Entry(hexapodTab, text="Speed in mm/s")
        # self.speedInput.pack(padx=10, pady=10)
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
        self.lockInTxtBx = tk.Text(lockInTab, height=8,  font=('Arial', 16))
        self.lockInTxtBx.pack(padx=10, pady=10)

        window.mainloop()

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
            json.dump({name: config.to_dict() for name, config in self.configurations.items()}, file, indent=4)

    def update_config(self):
        configName = self.configDropdown.get()
        self.instruments.set_current_fg_config(configName)
        self.instrumentsTxtBx.insert(tk.END, "Updated configuration to " + configName + "\n")
        self.instrumentsTxtBx.insert(tk.END, f"Frequency: {self.instruments.current_fg_config.frequency}\nAmplitude: {self.instruments.current_fg_config.amplitude}\nOffset: {self.instruments.current_fg_config.offset}\n\n")

    def create_config(self):
        config_name = self.configNameInput.get()
        freq = self.freqInput.get()
        amp = self.ampInput.get()
        offset = self.offsetInput.get()
        current_config = self.instruments.create_fg_config(config_name, freq, amp, offset)
        self.configurations[config_name] = current_config
        self.save_configurations()
        self.configDropdown['values'] = list(self.configurations.keys())
        self.configDropdown.set('')  # Clear the current selection
        self.instrumentsTxtBx.insert(tk.END, "Created configuration " + config_name + "\n")

    def connect_hexapod(self):
        global hexapod
        try:
            hexapod = HexapodControl()
        except Exception as e:
            self.hexapodTextbox.insert(tk.END, "Unable to connect to hexapod.\n Error: " + str(e) + "\n")

    def home_hexapod(self):
        if hexapod is None or not hexapod.ssh_API:
            print("Home")
        else:
            hexapod.home()

    def control_on_hexapod(self):
        if hexapod is None or not hexapod.ssh_API:
            print("Control On")
        else:
            hexapod.controlOn()

    def move_up(self):
        if hexapod is None or not hexapod.ssh_API:
            print("Move Up")
        else:
            hexapod.moveUp(self.stepInput.get())

    def move_down(self):
        if hexapod is None or not hexapod.ssh_API:
            print("Move Down")
        else:
            hexapod.moveDown(self.stepInput.get())

    def move_left(self):
        if hexapod is None or not hexapod.ssh_API:
            print("Move Left")
        else:
            hexapod.moveLeft(self.stepInput.get())

    def move_right(self):
        if hexapod is None or not hexapod.ssh_API:
            print("Move Right")
        else:
            hexapod.moveRight(self.stepInput.get())

    def move_in(self):
        if hexapod is None or not hexapod.ssh_API:
            print("Move In")
        else:
            hexapod.moveIn(self.stepInput.get())

    def move_out(self):
        if hexapod is None or not hexapod.ssh_API:
            print("Move Out")
        else:
            hexapod.moveOut(self.stepInput.get())
    def reset_position(self):
        if hexapod is None or not hexapod.ssh_API:
            print("Reset Position")
        else:
            hexapod.resetPosition()


if __name__ == '__main__':
    MicroscopeGUI()