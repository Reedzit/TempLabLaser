import matlab.engine
import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import numpy as np

#GUI Stuff
# window = tk.Tk()
# window.geometry(f"{window.winfo_screenwidth()}x{window.winfo_screenheight()}")
# window.title("Matlab Analysis")

eng = matlab.engine.start_matlab()
filepath = "C:/Users/reedg/OneDrive/Desktop/TEMPLab/templablaser/matlab"
eng.cd(filepath, nargout=0)
figure1data, figure2data, figure3data = eng.probe_data_python(nargout=3)
eng.quit()
figure1data = np.array(figure1data)
figure2data = np.array(figure2data)
figure3data = np.array(figure3data)


# data prep for surface plot
x1 = np.linspace(0, 1, len(figure1data))
y1 = np.linspace(0, 1, len(figure1data))
x1, y1 = np.meshgrid(x1,y1)
x2 = np.linspace(0, 1, len(figure2data))
y2 = np.linspace(0, 1, len(figure2data))
x2, y2 = np.meshgrid(x2,y2)
x3 = np.linspace(0, 1, len(figure3data[0]))
y3 = np.linspace(0, 1, len(figure3data))
x3, y3 = np.meshgrid(x3,y3)


fig1 = plt.figure(figsize=(15, 10))
fig2 = plt.figure(figsize=(15, 10))
fig3 = plt.figure(figsize=(15, 10))



# Create a 3D subplot for figure 1
ax1 = fig1.add_subplot(111, projection='3d')  # 1 row, 3 columns, 1st subplot
surf1 = ax1.plot_surface(x1, y1, figure1data, cmap='viridis', edgecolor='none')
ax1.set_title('Phase')
ax1.set_xlabel('X-axis')
ax1.set_ylabel('Y-axis')
ax1.set_zlabel('Z-axis')
fig1.colorbar(surf1, ax=ax1, shrink=0.5, aspect=10)  # Add color bar

# Create a 3D subplot for figure 2
ax2 = fig2.add_subplot(111, projection='3d')  # 1 row, 3 columns, 2nd subplot
surf2 = ax2.plot_surface(x2, y2, figure2data, cmap='plasma')
ax2.set_title('Amplitude')
ax2.set_xlabel('X-axis')
ax2.set_ylabel('Y-axis')
ax2.set_zlabel('Z-axis')
fig2.colorbar(surf2, ax=ax2, shrink=0.5, aspect=10)  # Add color bar

# Create a 3D subplot for figure 3
ax3 = fig3.add_subplot(111, projection='3d')  # 1 row, 3 columns, 3rd subplot
surf3 = ax3.plot_surface(x3, y3, figure3data, cmap='inferno', edgecolor='none')
ax3.set_title('Phase Jumps')
ax3.set_xlabel('X-axis')
ax3.set_ylabel('Y-axis')
ax3.set_zlabel('Z-axis')
fig3.colorbar(surf3, ax=ax3, shrink=0.5, aspect=10)  # Add color bar

# Adjust layout to prevent overlap
plt.tight_layout()

# Show the plot in a new window
plt.show()

#3d plot stuff
# fig = Figure(figsize=(10,8), dpi=100)
# ax = fig.add_subplot(111, projection='3d')
# surf = ax.plot_surface(x1,y1,figure1data, cmap='viridis')
# ax.set_title("practice")
# canvas = FigureCanvasTkAgg(fig, master=window)
# canvas.draw()
# canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)
# window.mainloop()

