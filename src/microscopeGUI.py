import tkinter as tk
import tkinter.filedialog
from tkinter import ttk
from PIL import Image, ImageTk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from instrumentInitialize import InstrumentInitialize
from instrument_configurations.fgConfig import fgConfig
from hexapod.hexapodControl import HexapodControl
import json
import os
import datetime
import sys
import threading
import queue
from graph_box import GraphBox
# import pymeasure.instruments.srs.sr830 as lia

def automation_popup():
    popup = tk.Toplevel()
    popup.title("Pop-up Window")
    image_path = os.path.join(sys.path[0],"res/HeMan.gif")
    img = tk.PhotoImage(file=image_path)
    popup.image = img
    label = tk.Label(popup, image=img)
    label.pack()
    print()

class MicroscopeGUI():
    CONFIG_FILE = "src\\instrument_configurations\\configs.json"
    instruments = InstrumentInitialize()
    hexapod = None

    def __init__(self):
        self.AutomationThread = None # Thread for automation, If not in use, should be None
        self.GraphingThread = None # Thread for updating the graph
        self.load_configs()

        window = tk.Tk()
        window.geometry("1000x1000")
        window.title("Microscope GUI")
        notebook = ttk.Notebook(window)

        instrumentsTab = tk.Frame(notebook)
        hexapodTab = tk.Frame(notebook)
        lockInTab = tk.Frame(notebook)
        automateTab = tk.Frame(notebook)

        notebook.add(instrumentsTab, text='Instruments')
        notebook.add(hexapodTab, text='Hexapod')
        notebook.add(lockInTab, text='Lock In Amplifier')
        notebook.add(automateTab, text='🤖Automation🤖')
        notebook.pack(expand=1, fill='both')

        ### Instruments Tab ###
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

        ### Hexapod Tab ###
        self.connectBtn = tk.Button(hexapodTab, text="Connect to Hexapod", command=self.connect_hexapod)
        self.connectBtn.pack(padx=10, pady=10)
        self.homeBtn = tk.Button(hexapodTab, text="Home Hexapod", command=self.home_hexapod)
        self.homeBtn.pack(padx=10, pady=10)
        self.controlOnBtn = tk.Button(hexapodTab, text="Turn on Control (Press this after homing)",
                                      command=self.control_on_hexapod)
        self.controlOnBtn.pack(padx=10, pady=10)
        self.stepLabel = tk.Label(hexapodTab, text="Step Size (mm)")
        self.stepLabel.pack(padx=10, pady=5)
        self.stepInput = tk.Entry(hexapodTab)
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
        btn_up.grid(row=0, column=1, sticky=tk.W + tk.E)

        btn_left = tk.Button(bfTranslation, text="Left", command=self.move_left, font=('Arial', 18))
        btn_left.grid(row=1, column=0, sticky=tk.W + tk.E)

        btn_down = tk.Button(bfTranslation, text="Down", command=self.move_down, font=('Arial', 18))
        btn_down.grid(row=1, column=1, sticky=tk.W + tk.E)

        btn_right = tk.Button(bfTranslation, text="Right", command=self.move_right, font=('Arial', 18))
        btn_right.grid(row=1, column=2, sticky=tk.W + tk.E)

        btn_in = tk.Button(bfTranslation, text="In", command=self.move_in, font=('Arial', 18))
        btn_in.grid(row=2, column=1, sticky=tk.W + tk.E)

        btn_out = tk.Button(bfTranslation, text="Out", command=self.move_out, font=('Arial', 18))
        btn_out.grid(row=3, column=1, sticky=tk.W + tk.E)

        bfTranslation.pack(fill='x', padx=20, pady=20)

        self.hexapodTextbox = tk.Text(hexapodTab, height=8, font=('Arial', 16))
        self.hexapodTextbox.pack(padx=10, pady=10)

        ### Lock In Amplifier Tab ###
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

        ### Automation Tab ###

        self.startLabel = tk.Label(automateTab, text="INITIAL VALUE")
        self.startLabel.grid(row=2, column=1, padx=10, pady=0)
        self.endLabel = tk.Label(automateTab, text="FINAL VALUE")
        self.endLabel.grid(row=2, column=2, padx=10, pady=0)

        self.freqLabelAuto = tk.Label(automateTab, text="Frequency (Hz)")
        self.freqLabelAuto.grid(row=3, column=0, padx=10, pady=5, sticky=tk.E)
        self.freqInitialInput = tk.Entry(automateTab)
        self.freqInitialInput.grid(row=3, column=1, padx=10, pady=5)
        self.freqFinalInput = tk.Entry(automateTab)
        self.freqFinalInput.grid(row=3, column=2, padx=10, pady=5)

        self.ampLabel = tk.Label(automateTab, text="Amplitude (V)")
        self.ampLabel.grid(row=4, column=0, padx=10, pady=10, sticky=tk.E)
        self.ampInitialInput = tk.Entry(automateTab)
        self.ampInitialInput.grid(row=4, column=1, padx=10, pady=5)
        self.ampFinalInput = tk.Entry(automateTab)
        self.ampFinalInput.grid(row=4, column=2, padx=10, pady=5)

        self.offsetLabelAuto = tk.Label(automateTab, text="Offset (V)")
        self.offsetLabelAuto.grid(row=5, column=0, padx=10, pady=5, sticky=tk.E)
        self.offsetInitialInput = tk.Entry(automateTab)
        self.offsetInitialInput.grid(row=5, column=1, padx=10, pady=5)
        self.offsetFinalInput = tk.Entry(automateTab)
        self.offsetFinalInput.grid(row=5, column=2, padx=10, pady=5)

        self.startMeasurements = tk.Button(automateTab, text="Start Measurements", state = "disabled" ,command=self.begin_automation)
        self.startMeasurements.grid(row=6, column=1, columnspan=1, padx=10, pady=10)
        self.endMeasurements = tk.Button(automateTab, text="End Measurements", state = "disabled", command=self.end_automation)
        self.endMeasurements.grid(row=6, column=2, columnspan=2, padx=10, pady=10)

        self.phaseLabel = tk.Label(automateTab, text="Adjust Channel 2 Phase (degrees)")
        self.phaseLabel.grid(row=7, column=0, padx=10, pady=10, sticky=tk.E)
        self.phaseInput = tk.Entry(automateTab)
        self.phaseInput.grid(row=7, column=1, padx=10, pady=10)
        self.setPhaseBtn = tk.Button(automateTab, text="Set Phase", command=self.set_phase)
        self.setPhaseBtn.grid(row=7, column=2, padx=10, pady=10)

        self.OutputLabel = tk.Label(automateTab, text="Status:")
        self.OutputLabel.grid(row=8, column=0)
        self.automationTxtBx = tk.Text(automateTab, height=8, font=('Arial', 16))
        self.automationTxtBx.grid(row=9, column=0, columnspan=4, padx=10, pady=10)

        self.stepCountLabel = tk.Label(automateTab, text="Step Count:")
        self.stepCount = tk.IntVar(automateTab, 1)
        self.stepCountInput = tk.Entry(automateTab, textvariable=self.stepCount)
        self.stepCountInput.grid(row=12, column=1, padx=10, pady=10)
        self.stepCountLabel.grid(row=12, column=0, padx=10, pady=10)
        self.timePerStep = tk.IntVar(automateTab, 1)
        self.timePerStepLabel = tk.Label(automateTab, text="Time Per Step (s):")
        self.timePerStepInput = tk.Entry(automateTab,textvariable= self.timePerStep, state='disabled')
        self.timePerStepInput.grid(row=11, column=1, padx=10, pady=10)
        self.timePerStepLabel.grid(row=11, column=0, padx=10, pady=10)

        self.fileStorageLocation = tk.StringVar(automateTab, "No Location Given")
        self.fileStorageLabel = tk.Label(automateTab, textvariable=self.fileStorageLocation)
        self.fileStorageButton = tk.Button(automateTab, text="Choose File Location", command=self.select_file_location)
        self.fileStorageLabel.grid(row=10, column=2, columnspan=2, padx=10, pady=10)
        self.fileStorageButton.grid(row=10, column=1, padx=10, pady=10)

        self.graph = GraphBox(0, 0, 0, 800, 400)
        self.automationGraph = tk.Label(automateTab)
        self.automationGraph.grid(row=13, column=0, columnspan=4, padx=10, pady=10, sticky='nsew')

        # initialize
        self.timeConstantDropDown.set(self.instruments.time_constants[5])
        self.update_time_constant()
        self.gainDropDown.set(self.instruments.sensitivities[5])
        self.update_gain()

        window.after(100, self.schedule_automation_update)
        window.mainloop()

    def measure(self):
        amplitude, phase = self.instruments.take_measurement()
        self.lockInTxtBx.insert('1.0',
                                f"Time: {datetime.datetime.now().time()} Amplitude: {amplitude} Phase: {phase}\n")

    def begin_automation(self):
        print("Beginning Automation...")
        initial_freq = int(self.freqInitialInput.get())
        final_freq = int(self.freqFinalInput.get())
        initial_amp = int(self.ampInitialInput.get())
        final_amp = int(self.ampFinalInput.get())
        initial_offset = int(self.offsetInitialInput.get())
        final_offset = int(self.offsetFinalInput.get())

        # These one are single values
        timeStep =int(self.timePerStep.get())
        stepCount = int(self.stepCount.get())
        filepath = self.fileStorageLocation.get()

        # Construct tuples out of the inputs
        freq = (initial_freq, final_freq)
        amp = (initial_amp, final_amp)
        offset = (initial_offset, final_offset)

        self.AutomationThread = threading.Thread(target=self.instruments.automatic_measuring, args=(freq, amp, offset, timeStep, stepCount, filepath))
        self.AutomationThread.start()
        self.startMeasurements["state"] = "disabled"
        self.endMeasurements["state"] = "normal"
        self.stepCountInput["state"] = "normal"
        self.fileStorageButton["state"] = "disabled"
        self.fileStorageLabel["state"] = "disabled"
        self.automationTxtBx.insert('1.0', f"Starting Automation...\n")
        self.automationTxtBx.insert('1.0', f"Time Step: {timeStep}s\n")
        self.automationTxtBx.insert('1.0', f"Step Count: {stepCount}\n")

    def end_automation(self):
        print("Ending Automation...")
        self.instruments.q.put("stop")
        self.endMeasurements["state"] = "disabled"
        self.startMeasurements["state"] = "normal"

    def select_file_location(self):
        filePath = tk.filedialog.askdirectory()
        if filePath == "":
            self.startMeasurements["state"] = "disabled"
            return
        else:
            self.fileStorageLocation.set(filePath)
            print(self.fileStorageLocation)
            self.startMeasurements["state"] = "normal"

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

    def update_automation_graph(self):
        image_path = os.path.join(sys.path[0], "temp.png")
        image = Image.open(image_path)
        photo = ImageTk.PhotoImage(image)
        self.automationGraph.configure(image=photo)
        self.automationGraph.image = photo  # Keep a reference!

    def update_automation_textbox(self, values):
            self.automationTxtBx.delete(1.0, tk.END)
            current_time, current_Step, freqIn, ampIn, offsetIn, amplitude, phase = values
            self.automationTxtBx.insert(tk.END, f"""
            @{current_time} ({current_Step} step(s)/{self.stepCount} step(s)):
            Input:
            Frequency: {freqIn} Hz | Amplitude: {ampIn} V | Offset: {offsetIn} V
            Output:
            Amplitude: {amplitude} V | Phase: {phase} degrees
""")

    def schedule_automation_update(self):
        if not self.instruments.automationQueue.empty():
            try:
                values = self.instruments.automationQueue.get()
                current_time, current_Step, freqIn, ampIn, offsetIn, amplitude, phase = values
                self.update_automation_textbox(values)

                # Update graph data
                print("Updating graph with new values...")
                self.graph.update_graph(amplitude, phase, current_Step)

                # Update the image display
                try:
                    plots_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'plots')
                    image_path = os.path.join(plots_dir, "temp.png")
                    print(f"Looking for graph image at: {image_path}")

                    if os.path.exists(image_path):
                        print("Found graph image, updating display...")
                        image = Image.open(image_path)
                        # Resize image to fit the label
                        image = image.resize((800, 400), Image.Resampling.LANCZOS)
                        photo = ImageTk.PhotoImage(image)
                        self.automationGraph.configure(image=photo)
                        self.automationGraph.image = photo  # Keep a reference
                        print("Graph display updated")
                    else:
                        print(f"Graph image not found at {image_path}")

                except Exception as e:
                    print(f"Error updating graph display: {e}")

            except queue.Empty:
                pass
            except Exception as e:
                print(f"Error in automation update: {e}")

        # Schedule the next update
        self.automationTxtBx.after(100, self.schedule_automation_update)


if __name__ == '__main__':
    MicroscopeGUI()
