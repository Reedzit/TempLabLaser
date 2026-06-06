import os

import matlab.engine
import matplotlib.pyplot as plt
import numpy as np
MATLAB_DIR = os.path.dirname(os.path.abspath(__file__))


def _build_surface_axes(data):
	x = np.linspace(0, 1, len(data))
	y = np.linspace(0, 1, len(data))
	return np.meshgrid(x, y)


def run_analysis(show_plot=True):
	eng = matlab.engine.start_matlab()
	try:
		eng.cd(MATLAB_DIR, nargout=0)
		figure1data, figure2data, figure3data = eng.probe_data_python(nargout=3)
	finally:
		eng.quit()

	figure1data = np.array(figure1data)
	figure2data = np.array(figure2data)
	figure3data = np.array(figure3data)

	x1, y1 = _build_surface_axes(figure1data)
	x2, y2 = _build_surface_axes(figure2data)
	x3 = np.linspace(0, 1, len(figure3data[0]))
	y3 = np.linspace(0, 1, len(figure3data))
	x3, y3 = np.meshgrid(x3, y3)

	fig1 = plt.figure(figsize=(15, 10))
	fig2 = plt.figure(figsize=(15, 10))
	fig3 = plt.figure(figsize=(15, 10))

	ax1 = fig1.add_subplot(111, projection='3d')
	surf1 = ax1.plot_surface(x1, y1, figure1data, cmap='viridis', edgecolor='none')
	ax1.set_title('Phase')
	ax1.set_xlabel('X-axis')
	ax1.set_ylabel('Y-axis')
	ax1.set_zlabel('Z-axis')
	fig1.colorbar(surf1, ax=ax1, shrink=0.5, aspect=10)

	ax2 = fig2.add_subplot(111, projection='3d')
	surf2 = ax2.plot_surface(x2, y2, figure2data, cmap='plasma')
	ax2.set_title('Amplitude')
	ax2.set_xlabel('X-axis')
	ax2.set_ylabel('Y-axis')
	ax2.set_zlabel('Z-axis')
	fig2.colorbar(surf2, ax=ax2, shrink=0.5, aspect=10)

	ax3 = fig3.add_subplot(111, projection='3d')
	surf3 = ax3.plot_surface(x3, y3, figure3data, cmap='inferno', edgecolor='none')
	ax3.set_title('Phase Jumps')
	ax3.set_xlabel('X-axis')
	ax3.set_ylabel('Y-axis')
	ax3.set_zlabel('Z-axis')
	fig3.colorbar(surf3, ax=ax3, shrink=0.5, aspect=10)

	plt.tight_layout()

	if show_plot:
		plt.show()

	return figure1data, figure2data, figure3data


if __name__ == "__main__":
	run_analysis(show_plot=True)

