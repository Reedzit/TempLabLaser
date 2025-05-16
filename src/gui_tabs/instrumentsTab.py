import json
import os
from tkinter import ttk
import tkinter as tk

from src.instrument_configurations.fgConfig import fgConfig


class InstrumentsTab:
    CONFIG_FILE = "../src/instrument_configurations/configs.json"

    def __init__(self, parent, instruments):
        self.parent = parent
        self.instruments = instruments
        self.setup_ui()
        self.load_configs()

    def setup_ui(self):
        instrumentsTab = self.parent
        instruments = self.instruments

        self.configDropdown = ttk.Combobox(instrumentsTab,
                                           values=self.instruments.fgConfigNames)
        self.configDropdown.grid(row=0, column=1, padx=10, pady=10)
        self.updateConfigButton = tk.Button(instrumentsTab, text="Update Configuration", command=self.update_config)
        self.updateConfigButton.grid(row=0, column=2, padx=10, pady=10)

        self.deleteConfigBtn = tk.Button(instrumentsTab, text="Delete Configuration", command=self.delete_config)
        self.deleteConfigBtn.grid(row=0, column=3, padx=10, pady=10)

        self.createConfigLabel = tk.Label(instrumentsTab, text="Create Configuration")
        self.createConfigLabel.grid(row=1, column=0, columnspan=3, padx=10, pady=10)

        self.configNameLabel = tk.Label(instrumentsTab, text="Configuration Name")
        self.configNameLabel.grid(row=2, column=0, padx=10, pady=10, sticky=tk.E)
        self.configNameInput = tk.Entry(instrumentsTab)
        self.configNameInput.grid(row=2, column=1, padx=10, pady=10)

        self.freqLabel = tk.Label(instrumentsTab, text="Frequency (Hz)")
        self.freqLabel.grid(row=3, column=0, padx=10, pady=10, sticky=tk.E)
        self.freqInput = tk.Entry(instrumentsTab)
        self.freqInput.grid(row=3, column=1, padx=10, pady=10)

        self.ampLabel = tk.Label(instrumentsTab, text="Amplitude (V)")
        self.ampLabel.grid(row=4, column=0, padx=10, pady=10, sticky=tk.E)
        self.ampInput = tk.Entry(instrumentsTab)
        self.ampInput.grid(row=4, column=1, padx=10, pady=10)

        self.offsetLabel = tk.Label(instrumentsTab, text="Offset (V)")
        self.offsetLabel.grid(row=5, column=0, padx=10, pady=10, sticky=tk.E)
        self.offsetInput = tk.Entry(instrumentsTab)
        self.offsetInput.grid(row=5, column=1, padx=10, pady=10)

        self.createConfigButton = tk.Button(instrumentsTab, text="Create Configuration", command=self.create_config)
        self.createConfigButton.grid(row=6, column=0, columnspan=3, padx=10, pady=10)

        self.phaseLabel = tk.Label(instrumentsTab, text="Adjust Channel 2" \
                                                        " Phase (degrees)")
        self.phaseLabel.grid(row=7, column=0, padx=10, pady=10, sticky=tk.E)
        self.phaseInput = tk.Entry(instrumentsTab)
        self.phaseInput.grid(row=7, column=1, padx=10, pady=10)
        self.setPhaseBtn = tk.Button(instrumentsTab, text="Set Phase", command=self.set_phase)
        self.setPhaseBtn.grid(row=7, column=2, padx=10, pady=10)

        self.instrumentsTxtBx = tk.Text(instrumentsTab, height=8, font=('Arial', 16))
        self.instrumentsTxtBx.grid(row=8, column=0, columnspan=4, padx=10, pady=10)

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
        self.instrumentsTxtBx.insert(tk.END,
                                     f"Frequency: {self.instruments.current_fg_config.frequency}\nAmplitude: {self.instruments.current_fg_config.amplitude}\nOffset: {self.instruments.current_fg_config.offset}\n\n")

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