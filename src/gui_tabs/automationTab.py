import tkinter as tk
import tkinter.filedialog
from PIL import Image, ImageTk
import os
import sys
import threading
import queue
from src.gui_tabs.graph_box import GraphBox
import time

def automation_popup():
    popup = tk.Toplevel()
    popup.title("Pop-up Window")
    image_path = os.path.join(sys.path[0], "res\\HeMan.png")
    print(image_path)
    img = tk.PhotoImage(file=image_path)
    popup.image = img
    label = tk.Label(popup, image=img)
    label.pack()


class AutomationTab:
    def __init__(self, parent, instruments):
        self.parent = parent
        self.instruments = instruments
        self.setup_ui()

    def setup_ui(self):
        automate_tab = self.parent
        self.start_label = tk.Label(automate_tab, text="INITIAL VALUE")
        self.start_label.grid(row=2, column=1, padx=10, pady=0)
        self.end_label = tk.Label(automate_tab, text="FINAL VALUE")
        self.end_label.grid(row=2, column=2, padx=10, pady=0)

        self.freq_label_auto = tk.Label(automate_tab, text="Frequency (Hz)")
        self.freq_label_auto.grid(row=3, column=0, padx=10, pady=5, sticky=tk.E)
        self.freqInitialInput = tk.Entry(automate_tab)
        self.freqInitialInput.grid(row=3, column=1, padx=10, pady=5)
        self.freqFinalInput = tk.Entry(automate_tab)
        self.freqFinalInput.grid(row=3, column=2, padx=10, pady=5)

        self.ampLabel = tk.Label(automate_tab, text="Amplitude (V)")
        self.ampLabel.grid(row=4, column=0, padx=10, pady=10, sticky=tk.E)
        self.ampInitialInput = tk.Entry(automate_tab)
        self.ampInitialInput.insert(-1, "4.8")
        self.ampInitialInput.grid(row=4, column=1, padx=10, pady=5)
        self.ampFinalInput = tk.Entry(automate_tab)
        self.ampFinalInput.insert(-1, "4.8")
        self.ampFinalInput.grid(row=4, column=2, padx=10, pady=5)

        self.offsetLabelAuto = tk.Label(automate_tab, text="Offset (V)")
        self.offsetLabelAuto.grid(row=5, column=0, padx=10, pady=5, sticky=tk.E)
        self.offsetInitialInput = tk.Entry(automate_tab)
        self.offsetInitialInput.insert(-1, "2.5")
        self.offsetInitialInput.grid(row=5, column=1, padx=10, pady=5)
        self.offsetFinalInput = tk.Entry(automate_tab)
        self.offsetFinalInput.insert(-1, "2.5")
        self.offsetFinalInput.grid(row=5, column=2, padx=10, pady=5)

        self.startMeasurements = tk.Button(automate_tab, text="Start Measurements", state="disabled",
                                           command=self.begin_automation)
        self.startMeasurements.grid(row=6, column=1, columnspan=1, padx=10, pady=10)
        self.endMeasurements = tk.Button(automate_tab, text="End Measurements", state="disabled",
                                         command=self.end_automation)
        self.endMeasurements.grid(row=6, column=2, columnspan=2, padx=10, pady=10)

        self.laserDistanceLabel = tk.Label(automate_tab, text="Distance between lasers (mm)")
        self.laserDistanceLabel.grid(row=7, column=0, padx=10, pady=10, sticky=tk.E)
        self.distanceInput = tk.Entry(automate_tab)
        self.distanceInput.grid(row=7, column=1, padx=10, pady=10)

        self.OutputLabel = tk.Label(automate_tab, text="Status:")
        self.OutputLabel.grid(row=8, column=0)
        self.automationTxtBx = tk.Text(automate_tab, height=8, font=('Arial', 16))
        self.automationTxtBx.grid(row=9, column=0, columnspan=4, padx=10, pady=10)

        self.stepCountLabel = tk.Label(automate_tab, text="Step Count:")
        self.stepCount = tk.IntVar(automate_tab, 1)
        self.stepCountInput = tk.Entry(automate_tab, textvariable=self.stepCount, state='disabled')
        self.stepCountInput.grid(row=12, column=1, padx=10, pady=10)
        self.stepCountLabel.grid(row=12, column=0, padx=10, pady=10)
        self.timePerStep = tk.IntVar(automate_tab, 1)
        self.timePerStepLabel = tk.Label(automate_tab, text="Time Per Step (s):")
        self.timePerStepInput = tk.Entry(automate_tab, textvariable=self.timePerStep, state='disabled')
        self.timePerStepInput.grid(row=11, column=1, padx=10, pady=10)
        self.timePerStepLabel.grid(row=11, column=0, padx=10, pady=10)

        self.fileStorageLocation = tk.StringVar(automate_tab, "No Location Given")
        self.fileStorageLabel = tk.Label(automate_tab, textvariable=self.fileStorageLocation)
        self.fileStorageButton = tk.Button(automate_tab, text="Choose File Location", command=self.select_file_location)
        self.fileStorageLabel.grid(row=10, column=2, columnspan=2, padx=10, pady=10)
        self.fileStorageButton.grid(row=10, column=1, padx=10, pady=10)

        print(self.distanceInput.get())
        self.graph = GraphBox(1)
        self.automationGraph = tk.Label(automate_tab)
        self.automationGraph.grid(row=13, column=0, columnspan=4, padx=10, pady=10, sticky='nsew')

    def begin_automation(self):
        print("Beginning Automation...")
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

        # Construct tuples out of the inputs
        freq = (initial_freq, final_freq)
        amp = (initial_amp, final_amp)
        offset = (initial_offset, final_offset)

        self.AutomationThread = threading.Thread(target=self.instruments.automatic_measuring,
                                                 args=(freq, amp, offset, timeStep, stepCount, filepath))
        self.AutomationThread.start()
        self.startMeasurements["state"] = "disabled"
        self.endMeasurements["state"] = "normal"
        self.stepCountInput["state"] = "normal"
        self.fileStorageButton["state"] = "disabled"
        self.fileStorageLabel["state"] = "disabled"
        self.automationTxtBx.insert('1.0', f"Starting Automation...\n")
        self.automationTxtBx.insert('1.0', f"Time Step: {timeStep}s\n")
        self.automationTxtBx.insert('1.0', f"Step Count: {stepCount}\n")

        automation_popup()

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

        # Clear the graph display
        self.graph.clear_graph()
        self.automationGraph.configure(image='')
        self.automationGraph.image = None

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
            self.timePerStepInput["state"] = "normal"
            self.stepCountInput["state"] = "normal"
            self.startMeasurements["state"] = "normal"

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
            @{current_time} ({current_Step} step(s)/{self.stepCount.get()} step(s)):
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
                self.graph.update_graph(amplitude, phase, current_Step, freqIn)

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