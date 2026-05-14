import tkinter as tk
import tkinter.filedialog

import pandas
import pandas as pd
from PIL import Image, ImageTk
import os
import sys
import threading
import multiprocessing
import queue
from src.gui_tabs.graph_box import GraphBox
import time
from tkinter import ttk


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SAMPLE_OPTIONS_PATH = os.path.join(PROJECT_ROOT, "res", "Sample Options.csv")


class AutomationTab:
    def __init__(self, parent, instruments, main_gui):
        self.graph = GraphBox(1,"Default")
        self.parent = parent
        self.instruments = instruments
        self.setup_ui()

    def setup_ui(self):
        automate_tab = self.parent
    
        # Create a main frame to hold the canvas
        main_frame = tk.Frame(automate_tab)
        main_frame.pack(fill=tk.BOTH, expand=1)
        
        # Create a canvas
        canvas = tk.Canvas(main_frame)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)
        
        # Add a scrollbar to the canvas
        scrollbar = tk.Scrollbar(main_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Configure the canvas
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Create a frame inside the canvas to hold the widgets
        inner_frame = tk.Frame(canvas)
        canvas.create_window((0, 0), window=inner_frame, anchor='nw')

        # Create LabelFrames for different sections
        input_frame = ttk.LabelFrame(inner_frame, text="Measurement Parameters")
        input_frame.grid(row=0, column=0, columnspan=4, padx=10, pady=5, sticky='nsew')

        control_frame = ttk.LabelFrame(inner_frame, text="Measurement Control")
        control_frame.grid(row=1, column=0, columnspan=4, padx=10, pady=5, sticky='nsew')

        output_frame = ttk.LabelFrame(inner_frame, text="Output and Status")
        output_frame.grid(row=2, column=0, columnspan=4, padx=10, pady=5, sticky='nsew')

        # Parameter inputs (in input_frame)
        self.start_label = tk.Label(input_frame, text="INITIAL VALUE")
        self.start_label.grid(row=0, column=1, padx=10, pady=0)
        self.end_label = tk.Label(input_frame, text="FINAL VALUE")
        self.end_label.grid(row=0, column=2, padx=10, pady=0)

        self.freq_label_auto = tk.Label(input_frame, text="Frequency (Hz)")
        self.freq_label_auto.grid(row=1, column=0, padx=10, pady=5, sticky=tk.E)
        self.freqInitialInput = tk.Entry(input_frame)
        self.freqInitialInput.grid(row=1, column=1, padx=10, pady=5)
        self.freqFinalInput = tk.Entry(input_frame)
        self.freqFinalInput.grid(row=1, column=2, padx=10, pady=5)
        self.freqInitialInput.insert(-1, "1")
        self.freqFinalInput.insert(-1, "102000")

        spacing_selector_options = ["linspace", "logspace"]
        self.spacing_selector_var = tk.StringVar(input_frame, "linspace")
        self.spacing_selector = tk.OptionMenu(input_frame, self.spacing_selector_var, *spacing_selector_options)
        self.spacing_selector.grid(row=1, column=3, padx=10, pady=10)

        self.ampLabel = tk.Label(input_frame, text="Amplitude (V)")
        self.ampLabel.grid(row=2, column=0, padx=10, pady=10, sticky=tk.E)
        self.ampInitialInput = tk.Entry(input_frame)
        self.ampInitialInput.insert(-1, "4.8")
        self.ampInitialInput.grid(row=2, column=1, padx=10, pady=5)
        self.ampFinalInput = tk.Entry(input_frame)
        self.ampFinalInput.insert(-1, "4.8")
        self.ampFinalInput.grid(row=2, column=2, padx=10, pady=5)

        self.offsetLabelAuto = tk.Label(input_frame, text="Offset (V)")
        self.offsetLabelAuto.grid(row=3, column=0, padx=10, pady=5, sticky=tk.E)
        self.offsetInitialInput = tk.Entry(input_frame)
        self.offsetInitialInput.insert(-1, "2.5")
        self.offsetInitialInput.grid(row=3, column=1, padx=10, pady=5)
        self.offsetFinalInput = tk.Entry(input_frame)
        self.offsetFinalInput.insert(-1, "2.5")
        self.offsetFinalInput.grid(row=3, column=2, padx=10, pady=5)

        self.laserDistanceLabel = tk.Label(input_frame, text="Distance between lasers (um)")
        self.laserDistanceLabel.grid(row=4, column=0, padx=10, pady=10, sticky=tk.E)
        self.distanceInput = tk.Entry(input_frame)
        self.distanceInput.insert(0, "5.0")
        self.distanceInput.grid(row=4, column=1, padx=10, pady=10)

        self.laserAngleLabel = tk.Label(input_frame, text="Laser Angle (degrees from x)")
        self.laserAngleLabel.grid(row=4, column=2, padx=10, pady=10, sticky=tk.E)
        self.angleInput = tk.Entry(input_frame)
        self.angleInput.insert(0, "0.0")
        self.angleInput.grid(row=4, column=3, padx=10, pady=10)

        # Control section (in control_frame)
        self.startMeasurements = tk.Button(control_frame, text="Start Measurements", state="normal",
                                           command=lambda: self.begin_automation(begin=True))
        self.startMeasurements.grid(row=0, column=0, padx=10, pady=10)
        self.endMeasurements = tk.Button(control_frame, text="End Measurements", state="disabled",
                                         command=self.end_automation)
        self.endMeasurements.grid(row=0, column=1, padx=10, pady=10)

        self.wait_for_convergence = tk.BooleanVar(control_frame, False)
        self.wait_for_convergence_check = tk.Checkbutton(control_frame, text="Wait for Convergence?",
                                                         variable=self.wait_for_convergence, onvalue=True, offvalue=False)
        self.wait_for_convergence_check.grid(row=1, column=1, padx=10, pady=10)

        self.timePerStep = tk.IntVar(control_frame, 1)
        self.timePerStepLabel = tk.Label(control_frame, text="Time Per Step (s):")
        self.timePerStepInput = tk.Entry(control_frame, textvariable=self.timePerStep, state='normal')
        self.timePerStepInput.grid(row=1, column=0, padx=10, pady=10)
        self.timePerStepLabel.grid(row=0, column=2, padx=10, pady=10)

        # Output section (in output_frame)
        self.OutputLabel = tk.Label(output_frame, text="Status:")
        self.OutputLabel.grid(row=0, column=0)
        self.automationTxtBx = tk.Text(output_frame, height=8, font=('Arial', 16))
        self.automationTxtBx.grid(row=1, column=0, columnspan=4, padx=10, pady=10)

        self.stepCountLabel = tk.Label(output_frame, text="Step Count:")
        self.stepCount = tk.IntVar(output_frame, 1)
        self.stepCountInput = tk.Entry(output_frame, textvariable=self.stepCount, state='normal')
        self.stepCountInput.grid(row=2, column=1, padx=10, pady=10)
        self.stepCountLabel.grid(row=2, column=0, padx=10, pady=10)

        graph_selector_options = ["Default", "Candlestick"]
        self.graph_selector_var = tk.StringVar(output_frame, "Default")
        self.graph_selector = tk.OptionMenu(output_frame, self.graph_selector_var, *graph_selector_options)
        self.graph_selector.grid(row=2, column=2, padx=10, pady=10)

        self.fileStorageLocation = tk.StringVar(output_frame, "C:\\Users\\templab\\Desktop\\Data")
        self.fileStorageLabel = tk.Label(output_frame, textvariable=self.fileStorageLocation)
        self.fileStorageButton = tk.Button(output_frame, text="Choose File Location", command=self.select_file_location)
        self.fileStorageLabel.grid(row=3, column=2, columnspan=2, padx=10, pady=10)
        self.fileStorageButton.grid(row=3, column=0, padx=10, pady=10)

        try:
            sample_options_df = pd.read_csv(SAMPLE_OPTIONS_PATH)
            sample_options = [x["Sample Name"] for x in sample_options_df.to_dict(orient="records")]
            if not sample_options:
                sample_options = ["NONE"]
        except Exception:
            sample_options = ["NONE"]
        self.sample_selector_var = tk.StringVar(output_frame, sample_options[0])
        self.sample_selector = tk.OptionMenu(output_frame, self.sample_selector_var, *sample_options)
        self.sample_selector.grid(row=2, column=3, padx=10, pady=10)
        
        self.generate_readme_button = tk.Button(output_frame, text="Generate README", command=self.generate_readme)
        self.generate_readme_button.grid(row=3, column=1, padx=10, pady=10)

        self.automationGraph = tk.Label(output_frame)
        self.automationGraph.grid(row=4, column=0, columnspan=4, padx=10, pady=10, sticky='nsew')

        # Change all your existing widget parents from automate_tab to inner_frame
        # For example:
        # Update scroll region when the size of the frame changes
        def _on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        
        inner_frame.bind('<Configure>', _on_frame_configure)
        
        # Bind mouse wheel to scroll
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

    def generate_readme(self):
        readme_generator = READMEGenerator()
        readme_generator.extra_info_pop_up(self)

    def generate_readme_automated(self, file_location):
        readme_generator = READMEGenerator()
        readme_generator.update_info(self, operator=os.environ.get("USERNAME", "Automated Operator"), photodiode_gain="10")
        readme_generator.generate_readme(file_location)

    def begin_automation(self, begin = False):
        print("Producing Correct File Organization...")
        def create_directory_structure(base_path, sample_name):
            if sample_name != "NONE":
                subdirectory_name = f"{sample_name}Date_{time.strftime('%b-%d-%Y')}"
            else:
                return base_path
            corrected_path = os.path.join(base_path, subdirectory_name)
            if not os.path.exists(corrected_path):
                print(f"Creating directory at: {corrected_path}")
                os.makedirs(corrected_path)
            measurement_name = f"Measurement_{time.strftime('%H-%M%p')}_BO{self.distanceInput.get()}um_Angle{self.angleInput.get()}deg"
            full_corrected_path = os.path.join(corrected_path, measurement_name)
            print(f"Creating measurement directory at: {full_corrected_path}")
            if not os.path.exists(full_corrected_path):
                os.makedirs(full_corrected_path)
            return full_corrected_path
        self.fileStorageLocation.set(create_directory_structure(self.fileStorageLocation.get(), self.sample_selector_var.get()))

        print("Beginning Automation...")
        print(f"Distance between lasers: {self.distanceInput.get()} um")
        print(f"Wait for convergence: {self.wait_for_convergence.get()}")
        if self.graph:
            self.graph.__del__()
        self.graph = GraphBox(self.distanceInput.get(), self.graph_selector_var.get())
        # Create a multiprocessing Queue to be able to pass images back and forth
        self.image_queue = self.manager.Queue()
        # Reset all data structures
        self.graph.amplitude_data = []
        self.graph.phase_data = []
        self.graph.step_data = []
        self.graph.frequency_data = []
        self.graph.diffusivity_estimates = []

        initial_freq = float(self.freqInitialInput.get())
        final_freq = float(self.freqFinalInput.get())
        initial_amp = float(self.ampInitialInput.get())
        final_amp = float(self.ampFinalInput.get())
        initial_offset = float(self.offsetInitialInput.get())
        final_offset = float(self.offsetFinalInput.get())

        # These one are single values
        timeStep = int(self.timePerStep.get())
        stepCount = int(self.stepCount.get())
        filepath = self.fileStorageLocation.get()
        spacing = self.spacing_selector_var.get()
        spot_distance = float(self.distanceInput.get())

        # Construct tuples out of the inputs
        freq = (initial_freq, final_freq)
        amp = (initial_amp, final_amp)
        offset = (initial_offset, final_offset)
        # Construct a single tuple that is going to be unpacked
        self.laser_settings = (freq, amp, offset, timeStep, stepCount, spot_distance, spacing)


        self.startMeasurements["state"] = "disabled"
        self.endMeasurements["state"] = "normal"
        self.stepCountInput["state"] = "normal"
        self.fileStorageButton["state"] = "disabled"
        self.fileStorageLabel["state"] = "disabled"
        self.automationTxtBx.insert('1.0', f"Starting Automation...\n")
        self.automationTxtBx.insert('1.0', f"Time Step: {timeStep}s\n")
        self.automationTxtBx.insert('1.0', f"Step Count: {stepCount}\n")

        # Write measurement metadata immediately so it lives with the data folder.
        self.generate_readme_automated(filepath)
        
        if begin == True:
            threading.Thread(target=self.instruments.automatic_measuring, 
                             args=(self.laser_settings, filepath, False)).start()


    def end_automation(self):
        print("Ending Automation...")
        # Put stop signal in queue in case automation is still going
        self.instruments.q.put("stop")

        # Give it some time
        time.sleep(0.5)

        # Clear both queues completely
        while not self.instruments.q.empty():
            try:
                self.instruments.q.get_nowait()
            except queue.Empty:
                break

        while not self.instruments.automationQueue.empty():
            try:
                self.instruments.automationQueue.get_nowait()
            except queue.Empty:
                break

        # Wait for automation to actually stop
        while self.instruments.automation_running:
            self.parent.after(100)  # Give time for automation to clean up

        # Reset all GUI elements
        self.endMeasurements["state"] = "disabled"
        self.startMeasurements["state"] = "normal"
        self.fileStorageButton["state"] = "normal"
        self.fileStorageLabel["state"] = "normal"
        self.timePerStepInput["state"] = "normal"
        self.stepCountInput["state"] = "normal"

        # Clear the automation queue
        while not self.instruments.automationQueue.empty():
            try:
                self.instruments.automationQueue.get_nowait()
            except queue.Empty:
                break

        # Reset graph data
        self.graph.amplitude_data = []
        self.graph.phase_data = []
        self.graph.step_data = []
        self.graph.frequency_data = []
        self.graph.diffusivity_estimates = []

        # Clear the graph data
        self.graph.clear_graph()
        self.graph.__del__() #Remove the graphing object in case they decide to make another one.

        # Reset the text box
        self.automationTxtBx.delete(1.0, tk.END)
        self.automationTxtBx.insert('1.0', "Automation completed.\nReady for new measurement.\n")

        # Clear all data from the instruments
        self.instruments.automation_status = None

    def select_file_location(self):
        filePath = tk.filedialog.askdirectory()
        if filePath == "":
            self.startMeasurements["state"] = "disabled"
            return
        else:
            self.fileStorageLocation.set(filePath)
            print(self.fileStorageLocation)

    def update_automation_graph(self):
        image = self.graph.plot_output.get_nowait()
        if image:
            # Resize image to fit the label
            image = image.resize((800, 400), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(image)
            self.automationGraph.configure(image=photo)
            self.automationGraph.image = photo  # Keep reference
            print("Graph display updated")

    def update_automation_textbox(self, values):
        self.automationTxtBx.delete(1.0, tk.END)
        latest = values.iloc[-1]
        current_time = latest.get("Time", "NA")
        current_Step = latest.get("index", "NA")
        freqIn = latest.get("FrequencyIn", "NA")
        amplitude = latest.get("AmplitudeOut", "NA")
        phase = latest.get("PhaseOut", "NA")
        real = latest.get("RealOut", "NA")
        imag = latest.get("ImagOut", "NA")
        convergence = latest.get("Convergence", "NA")
        rotation = latest.get("Degrees of Rotation", "NA")
        self.automationTxtBx.insert(tk.END, f"""
            @{current_time} ({current_Step} step(s)/{self.stepCount.get()} step(s)):
            Input:
            Frequency: {freqIn} Hz
            Output:
            Amplitude: {amplitude} V | Phase: {phase} degrees
            Real: {real} V | Imag: {imag} V
            Convergence: {convergence}
            Rotation: {rotation}
""")

    def schedule_automation_update(self):
        if not self.instruments.automationQueue.empty():
            print("Automation queue not empty")
            try:
                dataFrame = self.instruments.automationQueue.get()
                print(f"Received new data frame with shape: {dataFrame.shape}")

                # Update text display
                self.update_automation_textbox(dataFrame)

                # Update graph data
                pickle_loc = self.graph.PICKLE_FILE_LOCATION +"_"+self.spacing_selector_var.get() +".pickle"
                pd.to_pickle(dataFrame, pickle_loc)
                self.graph.data_queue.put_nowait(pickle_loc)
                print("Sent new data to plotting process")

            except queue.Empty:
                pass
            except Exception as e:
                print(f"Error processing automation data: {e}")

        # Try to update graph display independently of new data
        try:
            self.update_automation_graph()
        except queue.Empty:
            pass  # No new graph image available yet
        except Exception as e:
            print(f"Error updating graph display: {e}")

        # Schedule next update
        self.automationTxtBx.after(100, self.schedule_automation_update)

class READMEGenerator:
    """Collects and writes measurement metadata into a Markdown README file."""

    def __init__(self):
        self.operator = "NA"
        self.sample_id = "NA"
        self.sample_vendor = "NA"
        self.sample_gold_thickness = "NA"
        self.sample_notes = "NA"
        self.beam_offset = "NA"
        self.beam_angle = "NA"
        self.green_center = "NA"
        self.red_center = "NA"
        self.green_power = "NA"
        self.lowest_freq = "NA"
        self.highest_freq = "NA"
        self.freq_mode = "NA"
        self.lia_time_constant = "NA"
        self.lia_sensitivity = "NA"
        self.photodiode_gain = "NA"
        import datetime
        self.timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.save_path = "NA"
        self.lia_settings = {}

    @staticmethod
    def _safe_query(instrument, command):
        if instrument is None:
            return "Unavailable"
        try:
            return str(instrument.query(command)).strip()
        except Exception:
            return "Unavailable"

    def _collect_lia_settings(self, lia, instruments):
        if lia is None:
            self.lia_settings = {"Connection": "Unavailable"}
            return

        input_config_map = {
            "0": "A",
            "1": "A-B",
            "2": "I (1 MOhm)",
            "3": "I (100 MOhm)",
        }
        reserve_mode_map = {"0": "High Reserve", "1": "Normal", "2": "Low Noise"}
        filter_slope_map = {"0": "6 dB/oct", "1": "12 dB/oct", "2": "18 dB/oct", "3": "24 dB/oct"}
        ref_source_map = {"0": "External", "1": "Internal"}
        line_notch_map = {"0": "Off", "1": "Line", "2": "2x Line", "3": "Both"}
        coupling_map = {"0": "AC", "1": "DC"}
        shield_map = {"0": "Float", "1": "Ground"}
        sync_map = {"0": "Off", "1": "On"}
        sample_rate_map = {
            "0": "62.5 mHz", "1": "125 mHz", "2": "250 mHz", "3": "500 mHz",
            "4": "1 Hz", "5": "2 Hz", "6": "4 Hz", "7": "8 Hz",
            "8": "16 Hz", "9": "32 Hz", "10": "64 Hz", "11": "128 Hz",
            "12": "256 Hz", "13": "512 Hz", "14": "Trigger",
        }

        sens_code = self._safe_query(lia, "SENS?")
        tc_code = self._safe_query(lia, "OFLT?")

        sensitivity = "Unavailable"
        if sens_code.isdigit() and int(sens_code) < len(instruments.sensitivities):
            sensitivity = instruments.sensitivities[int(sens_code)]

        time_constant = "Unavailable"
        if tc_code.isdigit() and int(tc_code) < len(instruments.time_constants):
            time_constant = instruments.time_constants[int(tc_code)]

        self.lia_settings = {
            "Identification": self._safe_query(lia, "*IDN?"),
            "Reference Source": ref_source_map.get(self._safe_query(lia, "FMOD?"), self._safe_query(lia, "FMOD?")),
            "Reference Frequency (Hz)": self._safe_query(lia, "FREQ?"),
            "Reference Phase (deg)": self._safe_query(lia, "PHAS?"),
            "Harmonic": self._safe_query(lia, "HARM?"),
            "Sine Output Level (V)": self._safe_query(lia, "SLVL?"),
            "Input Configuration": input_config_map.get(self._safe_query(lia, "ISRC?"), self._safe_query(lia, "ISRC?")),
            "Input Shield": shield_map.get(self._safe_query(lia, "IGND?"), self._safe_query(lia, "IGND?")),
            "Input Coupling": coupling_map.get(self._safe_query(lia, "ICPL?"), self._safe_query(lia, "ICPL?")),
            "Line Notch Filters": line_notch_map.get(self._safe_query(lia, "ILIN?"), self._safe_query(lia, "ILIN?")),
            "Sensitivity": sensitivity,
            "Reserve Mode": reserve_mode_map.get(self._safe_query(lia, "RMOD?"), self._safe_query(lia, "RMOD?")),
            "Time Constant": time_constant,
            "Low Pass Slope": filter_slope_map.get(self._safe_query(lia, "OFSL?"), self._safe_query(lia, "OFSL?")),
            "Synchronous Filter": sync_map.get(self._safe_query(lia, "SYNC?"), self._safe_query(lia, "SYNC?")),
            "Sample Rate": sample_rate_map.get(self._safe_query(lia, "SRAT?"), self._safe_query(lia, "SRAT?")),
            "X Output (V)": self._safe_query(lia, "OUTP? 1"),
            "Y Output (V)": self._safe_query(lia, "OUTP? 2"),
            "R Output (V)": self._safe_query(lia, "OUTP? 3"),
            "Theta Output (deg)": self._safe_query(lia, "OUTP? 4"),
        }

    def extra_info_pop_up(self, parent):
        from tkinter import ttk
        grandpa = parent.parent # This is crap code but this is the main window
        def build_UI(self):
            self.popup = tk.Toplevel(grandpa)
            self.popup.title("Enter README Information")
            ttk.Label(self.popup, text="Operator:").grid(row=0, column=0)
            self.operator_entry = ttk.Entry(self.popup)
            self.operator_entry.grid(row=0, column=1)
            self.diode_gain_label = ttk.Label(self.popup, text="Photodiode Gain:")
            self.diode_gain_label.grid(row=1, column=0)
            self.diode_gain_entry = ttk.Entry(self.popup)
            self.diode_gain_entry.insert(0, "10")
            self.diode_gain_entry.grid(row=1, column=1)
            ttk.Button(self.popup, text="Submit", command=lambda:end_pop_up(self)).grid(row=10, column=0, columnspan=2)
        def end_pop_up(self):
            self.operator = str(self.operator_entry.get())
            self.photodiode_gain = str(self.diode_gain_entry.get())
            if self.operator == "":
                self.operator = "Someone that doesn't fill boxes in"
                print("No operator name provided;")
            self.popup.destroy()
            self.update_info(parent)
            self.generate_readme(parent.fileStorageLocation.get())
        build_UI(self)
        
    def update_info(self, parent, operator=None, photodiode_gain=None):
        laser_gui = parent
        if operator is not None:
            self.operator = str(operator)
        if photodiode_gain is not None:
            self.photodiode_gain = str(photodiode_gain)

        sample_record = pd.read_csv(SAMPLE_OPTIONS_PATH)
        self.sample_id = laser_gui.sample_selector_var.get()
        sample_info = sample_record.loc[sample_record["Sample Name"] == self.sample_id]
        if not sample_info.empty:
            self.sample_gold_thickness = sample_info["Gold Thickness"].values[0]
            self.sample_vendor = sample_info["Vendor"].values[0]
            self.sample_notes = sample_info["Details"].values[0]
        self.beam_offset = laser_gui.distanceInput.get()
        self.beam_angle = laser_gui.angleInput.get()
        self.green_center = "Computer Vision not implemented"
        self.red_center = "Computer Vision not implemented"
        self.green_power = "coherent connection not yet connected to GUI"
        self.lowest_freq = laser_gui.freqInitialInput.get()
        self.highest_freq = laser_gui.freqFinalInput.get()
        self.freq_mode = laser_gui.spacing_selector_var.get()
        lia = getattr(laser_gui.instruments, "lia", None)
        self._collect_lia_settings(lia, laser_gui.instruments)
        if lia is not None:
            try:
                self.lia_time_constant = str(lia.query("OFLT?"))
                self.lia_sensitivity = str(lia.query("SENS?"))
            except Exception:
                self.lia_time_constant = "Unavailable"
                self.lia_sensitivity = "Unavailable"
        else:
            self.lia_time_constant = "Unavailable"
            self.lia_sensitivity = "Unavailable"
        self.save_path = laser_gui.fileStorageLocation.get()

    def generate_readme(self, file_location):
        print("Collecting information for README...")
        print("Generating README...")
        lia_lines = "\n".join([f"{key}: {value}" for key, value in self.lia_settings.items()])
        readMe = f"""
############################################################
#                    MEASUREMENT README                    #
############################################################

## General Information

- Operator: {self.operator}
- Date & Time: {self.timestamp}

## Sample Information

- Sample ID: {self.sample_id}
- Sample Vendor: {self.sample_vendor}
- Sample Gold Thickness: {self.sample_gold_thickness}
- Notes on Sample: {self.sample_notes}

## Laser Information

- Beam Offset: {self.beam_offset}
- Beam Angle: {self.beam_angle}
- Green Center: {self.green_center}
- Red Center: {self.red_center}
- Green Power: {self.green_power}

## Equipment Settings

- Lowest Freq: {self.lowest_freq}
- Highest Freq: {self.highest_freq}
- Log or Linear: {self.freq_mode}
- LIA Time Constant: {self.lia_time_constant}
- LIA Sensitivity: {self.lia_sensitivity}
- PhotoDiode Gain: {self.photodiode_gain}

## Lock-In Amplifier Snapshot

{lia_lines}

############################################################
#                   END OF MEASUREMENT FILE                #
############################################################
""".strip()
        readme_path = os.path.join(file_location, "README.md")
        with open(readme_path, 'w') as f:
            f.write(readMe)
        print(f"README generated at {readme_path}")
