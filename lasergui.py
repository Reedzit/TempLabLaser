import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np
import subprocess
import threading
import os
from instrumentInitialize import InstrumentInitialize
# import matlabAnalysis


class LaserGUI:
  def __init__(self):
    self.instruments: InstrumentInitialize = InstrumentInitialize()
    
    self.window = tk.Tk()
    self.window.geometry("800x800")
    self.window.title("Microscope")
    label = tk.Label(self.window, text="Laser GUI", font=('Arial', 18))
    label.pack(padx=20, pady=20)
    self.buttonframe = tk.Frame(self.window)
    self.buttonframe.columnconfigure(0, weight=1)
    self.buttonframe.columnconfigure(1, weight=1)
    self.buttonframe.columnconfigure(2, weight=1)

    btn1 = tk.Button(self.buttonframe, text="Initialize System", command=self.initializeInstruments, font=('Arial', 18))
    btn1.grid(row=0, column=0, sticky=tk.W+tk.E)

    btn2 = tk.Button(self.buttonframe, text="Plot Collected Data",command=self.runMatlab, font=('Arial', 18))
    btn2.grid(row=0, column=1, sticky=tk.W+tk.E)

    btn3 = tk.Button(self.buttonframe, text="Move Hexapod", command=self.moveHexapod, font=('Arial', 18))
    btn3.grid(row=0, column=2, sticky=tk.W+tk.E)

    btn4 = tk.Button(self.buttonframe, text="Take Measurement", font=('Arial', 18))
    btn4.grid(row=1, column=0, sticky=tk.W+tk.E)

    btn5 = tk.Button(self.buttonframe, text="Placeholder", font=('Arial', 18))
    btn5.grid(row=1, column=1, sticky=tk.W+tk.E)
    self.buttonframe.pack(fill='x', padx=20, pady=20 )

    self.textbox = tk.Text(self.window, height=8,  font=('Arial', 16))
    self.textbox.pack(padx=10, pady=10, side=tk.BOTTOM, fill=tk.X)

    self.window.mainloop()

  def runMatlab(self):
    thread = threading.Thread(target=lambda: subprocess.run(['python', 'matlabAnalysis.py'], check=True))
    try: 
      thread.start()
    except subprocess.CalledProcessError as e:
      self.textbox.insert(tk.END, f"An error occurred: {e}")
      print(f"An error occurred: {e}")
    self.textbox.insert(tk.END, "Matlab Analysis Complete\n")

  def initializeInstruments(self):
    def run_script():
        try:
            script_path = os.path.join(os.path.dirname(__file__), 'instrumentInitialize.py')
            subprocess.run(['python', script_path], check=True)
            self.textbox.insert(tk.END, "Instruments Initializing\n")
        except subprocess.CalledProcessError as e:
            self.textbox.insert(tk.END, f"An error occurred: {e}\n")
            print(f"An error occurred: {e}")

    thread = threading.Thread(target=run_script)
    thread.start()

  def moveHexapod(self):
    try:
        # script_path = os.path.join(os.path.dirname(__file__), 'hexapodControl.py')
        # subprocess.run(['python', script_path], check=True)
        from hexapodControl import HexapodControlWindow
        HexapodControlWindow()
        self.textbox.insert(tk.END, "Hexapod Connected\n")
    except Exception as e:
        self.textbox.insert(tk.END, f"An error occurred: {e}\n")
        print(f"An error occurred: {e}")


