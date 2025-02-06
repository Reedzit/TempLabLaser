import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from instrumentInitialize import InstrumentInitialize
from instrument_configurations.fgConfig import fgConfig
from hexapodControl import HexapodControl
import json
import os

CONFIG_FILE = "templablaser\\instrument_configurations\\configs.json"

instruments = InstrumentInitialize()
hexapod = None

def load_configs():
    configurations = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            data = json.load(f)
            for name, config in data.items():
                current = fgConfig(name=config['name'], 
                                                frequency=float(config['frequency']),
                                                amplitude=float(config['amplitude']),
                                                offset=float(config['offset']))
                instruments.FgConfigs[name] = current
                configurations[name] = current
                instruments.fgConfigNames.append(name)
    return configurations

def save_configurations():
    with open(CONFIG_FILE, 'w') as file:
        json.dump({name: config.to_dict() for name, config in configurations.items()}, file, indent=4)

def update_config():
    configName = configDropdown.get()
    instruments.set_current_fg_config(configName)
    instrumentsTxtBx.insert(tk.END, "Updated configuration to " + configName + "\n")
    instrumentsTxtBx.insert(tk.END, f"Frequency: {instruments.current_fg_config.frequency}\nAmplitude: {instruments.current_fg_config.amplitude}\nOffset: {instruments.current_fg_config.offset}\n\n")

def create_config():
    config_name = configNameInput.get()
    freq = freqInput.get()
    amp = ampInput.get()
    offset = offsetInput.get()
    current_config = instruments.create_fg_config(config_name, freq, amp, offset)
    configurations[config_name] = current_config
    save_configurations()
    configDropdown['values'] = list(configurations.keys())
    configDropdown.set('')  # Clear the current selection
    instrumentsTxtBx.insert(tk.END, "Created configuration " + config_name + "\n")

def connect_hexapod():
    global hexapod
    try:
        hexapod = HexapodControl()
    except Exception as e:
        textbox.insert(tk.END, "Unable to connect to hexapod.\n Error: " + str(e) + "\n")

def home_hexapod():
    if hexapod is None or not hexapod.ssh_API:
        print("Home")
    else:
        hexapod.home()

def control_on_hexapod():
    if hexapod is None or not hexapod.ssh_API:
        print("Control On")
    else:
        hexapod.controlOn()

def move_up():
    if hexapod is None or not hexapod.ssh_API:
        print("Move Up")
    else:
        hexapod.moveUp(stepInput.get())

def move_down():
    if hexapod is None or not hexapod.ssh_API:
        print("Move Down")
    else:
        hexapod.moveDown(stepInput.get())

def move_left():
    if hexapod is None or not hexapod.ssh_API:
        print("Move Left")
    else:
        hexapod.moveLeft(stepInput.get())

def move_right():
    if hexapod is None or not hexapod.ssh_API:
        print("Move Right")
    else:
        hexapod.moveRight(stepInput.get())

def move_in():
    if hexapod is None or not hexapod.ssh_API:
        print("Move In")
    else:
        hexapod.moveIn(stepInput.get())

def move_out():
    if hexapod is None or not hexapod.ssh_API:
        print("Move Out")
    else:
        hexapod.moveOut(stepInput.get())

configurations = load_configs()

window = tk.Tk()
window.geometry("800x800")
window.title("Practice GUI")
notebook = ttk.Notebook(window)
instrumentsTab = tk.Frame(notebook)
hexapodTab = tk.Frame(notebook)
notebook.add(instrumentsTab, text='Instruments')
notebook.add(hexapodTab, text='Hexapod')
notebook.pack(expand=1, fill='both')

### Instruments Tab ###
configDropdown = ttk.Combobox(instrumentsTab, textvariable="Select a configuration", values=instruments.fgConfigNames)
configDropdown.grid(row=0, column=1, padx=10, pady=10)
updateConfigButton = tk.Button(instrumentsTab, text="Update Configuration", command=update_config)
updateConfigButton.grid(row=0, column=2, padx=10, pady=10)

createConfigLabel = tk.Label(instrumentsTab, text="Create Configuration")
createConfigLabel.grid(row=1, column=0, columnspan=3, padx=10, pady=10)

configNameLabel = tk.Label(instrumentsTab, text="Configuration Name")
configNameLabel.grid(row=2, column=0, padx=10, pady=10, sticky=tk.E)
configNameInput = tk.Entry(instrumentsTab, text="Name")
configNameInput.grid(row=2, column=1, padx=10, pady=10)

freqLabel = tk.Label(instrumentsTab, text="Frequency")
freqLabel.grid(row=3, column=0, padx=10, pady=10, sticky=tk.E)
freqInput = tk.Entry(instrumentsTab, text="Frequency")
freqInput.grid(row=3, column=1, padx=10, pady=10)

ampLabel = tk.Label(instrumentsTab, text="Amplitude")
ampLabel.grid(row=4, column=0, padx=10, pady=10, sticky=tk.E)
ampInput = tk.Entry(instrumentsTab, text="Amplitude")
ampInput.grid(row=4, column=1, padx=10, pady=10)

offsetLabel = tk.Label(instrumentsTab, text="Offset")
offsetLabel.grid(row=5, column=0, padx=10, pady=10, sticky=tk.E)
offsetInput = tk.Entry(instrumentsTab, text="Offset")
offsetInput.grid(row=5, column=1, padx=10, pady=10)

createConfigButton = tk.Button(instrumentsTab, text="Create Configuration", command=create_config)
createConfigButton.grid(row=6, column=0, columnspan=3, padx=10, pady=10)

instrumentsTxtBx = tk.Text(instrumentsTab, height=8,  font=('Arial', 16))
instrumentsTxtBx.grid(row=8, column=0, columnspan=4, padx=10, pady=10)
### Hexapod Tab ###
connectBtn = tk.Button(hexapodTab, text="Connect to Hexapod", command=connect_hexapod)
connectBtn.pack(padx=10, pady=10)
homeBtn = tk.Button(hexapodTab, text="Home Hexapod", command=home_hexapod)
homeBtn.pack(padx=10, pady=10)
controlOnBtn = tk.Button(hexapodTab, text="Turn on Control", command=control_on_hexapod)
controlOnBtn.pack(padx=10, pady=10)
stepLabel = tk.Label(hexapodTab, text="Step Size")
stepLabel.pack(padx=10, pady=5)
stepInput = tk.Entry(hexapodTab, text="Step Size")
stepInput.pack(padx=10, pady=10)

bfTranslation = tk.Frame(hexapodTab)
bfTranslation.columnconfigure(0, weight=1)
bfTranslation.columnconfigure(1, weight=1)
bfTranslation.columnconfigure(2, weight=1)
bfTranslation.rowconfigure(0, weight=1)
bfTranslation.rowconfigure(1, weight=1)
bfTranslation.rowconfigure(2, weight=1)

btn_up = tk.Button(bfTranslation, text="Up", command=move_up, font=('Arial', 18))
btn_up.grid(row=0, column=1, sticky=tk.W+tk.E)

btn_left = tk.Button(bfTranslation, text="Left", command=move_left, font=('Arial', 18))
btn_left.grid(row=1, column=0, sticky=tk.W+tk.E)

btn_down = tk.Button(bfTranslation, text="Down", command=move_down, font=('Arial', 18))
btn_down.grid(row=1, column=1, sticky=tk.W+tk.E)

btn_right = tk.Button(bfTranslation, text="Right", command=move_right, font=('Arial', 18))
btn_right.grid(row=1, column=2, sticky=tk.W+tk.E)

btn_in = tk.Button(bfTranslation, text="In", command=move_in, font=('Arial', 18))
btn_in.grid(row=2, column=1, sticky=tk.W+tk.E)

btn_out = tk.Button(bfTranslation, text="Out", command=move_out, font=('Arial', 18))
btn_out.grid(row=3, column=1, sticky=tk.W+tk.E)

bfTranslation.pack(fill='x', padx=20, pady=20)

textbox = tk.Text(hexapodTab, height=8,  font=('Arial', 16))
textbox.pack(padx=10, pady=10, side=tk.BOTTOM, fill=tk.X)

window.mainloop()