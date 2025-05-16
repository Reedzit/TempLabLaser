import tkinter as tk
import tkinter.filedialog
from PIL import Image, ImageTk
import os
import sys
import threading
import queue
from graph_box import GraphBox


class AutomationTab():
    def __init__(self, parent, instruments):
        self.parent = parent
        self.instruments = instruments
        self.setup_ui()

    def setup_ui(self):
        automateTab = self.parent
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

        self.startMeasurements = tk.Button(automateTab, text="Start Measurements", state="disabled",
                                           command=self.begin_automation)
        self.startMeasurements.grid(row=6, column=1, columnspan=1, padx=10, pady=10)
        self.endMeasurements = tk.Button(automateTab, text="End Measurements", state="disabled",
                                         command=self.end_automation)
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
        self.timePerStepInput = tk.Entry(automateTab, textvariable=self.timePerStep, state='disabled')
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

    def automation_popup(self):
        popup = tk.Toplevel()
        popup.title("Pop-up Window")
        image_path = os.path.join(sys.path[0], "res/HeMan.gif")
        img = tk.PhotoImage(file=image_path)
        popup.image = img
        label = tk.Label(popup, image=img)
        label.pack()

    def begin_automation(self):
        print("Beginning Automation...")
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

        self.automation_popup()

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

    def set_phase(self):
        phase = self.phaseInput.get()
        value = self.instruments.set_phase(phase)
        self.automationTxtBx.insert(tk.END, "Channel 2 phase set to " + str(value) + "\n")
