import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np
import subprocess
import threading
# import matlabAnalysis

#GUI Stuff
window = tk.Tk()
# window.geometry(f"{window.winfo_screenwidth()}x{window.winfo_screenheight()}")
window.geometry("800x800")
window.title("Laser GUI")

# #Practice Data
# def plot_3d():
#   x = np.linspace(-5,5,100)
#   y = np.linspace(-5,5,100)
#   x, y = np.meshgrid(x,y)
#   z = np.sin(np.sqrt(x**2 + y**2))

#   fig = Figure(figsize=(5,4), dpi=100)
#   ax = fig.add_subplot(111, projection='3d')
#   ax.plot_surface(x,y,z, cmap='viridis')
#   ax.set_title("practice")
#   canvas = FigureCanvasTkAgg(fig, master=window)
#   canvas.draw()
#   canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

def runMatlab():
  thread = threading.Thread(target=lambda: subprocess.run(['python', 'matlabAnalysis.py'], check=True))
  try: 
    thread.start()
  except subprocess.CalledProcessError as e:
    textbox.insert(tk.END, f"An error occurred: {e}")
    print(f"An error occurred: {e}")
  textbox.insert(tk.END, "Matlab Analysis Complete\n")

def initializeInstruments():
  thread = threading.Thread(target=lambda: subprocess.run(['python', 'instrumentInitialize.py'], check=True))
  try: 
    thread.start()
  except subprocess.CalledProcessError as e:
    textbox.insert(tk.END, f"An error occurred: {e}")
    print(f"An error occurred: {e}")
  textbox.insert(tk.END, "Instruments Initialized\n")

label = tk.Label(window, text="Laser GUI", font=('Arial', 18))
label.pack(padx=20, pady=20)



buttonframe = tk.Frame(window)
buttonframe.columnconfigure(0, weight=1)
buttonframe.columnconfigure(1, weight=1)
buttonframe.columnconfigure(2, weight=1)


btn1 = tk.Button(buttonframe, text="Initialize System", command=initializeInstruments, font=('Arial', 18))
btn1.grid(row=0, column=0, sticky=tk.W+tk.E)

btn2 = tk.Button(buttonframe, text="Plot Collected Data",command=runMatlab, font=('Arial', 18))
btn2.grid(row=0, column=1, sticky=tk.W+tk.E)

btn3 = tk.Button(buttonframe, text="Calibrate Laser", font=('Arial', 18))
btn3.grid(row=0, column=2, sticky=tk.W+tk.E)

btn4 = tk.Button(buttonframe, text="Take Measurement", font=('Arial', 18))
btn4.grid(row=1, column=0, sticky=tk.W+tk.E)

btn4 = tk.Button(buttonframe, text="Placeholder", font=('Arial', 18))
btn4.grid(row=1, column=1, sticky=tk.W+tk.E)
buttonframe.pack(fill='x', padx=20, pady=20)

textbox = tk.Text(window, height=8,  font=('Arial', 16))
textbox.pack(padx=10, pady=10)

window.mainloop()