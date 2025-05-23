import multiprocessing as mp
import queue
import os
from io import BytesIO
import sys
from multiprocessing.queues import Queue
from matplotlib import pyplot as plt
import numpy as np
from PIL import Image


def plotting_process(data_queue, plot_queue):
    """Separate process function for plotting"""
    while True:
        try:
            data = data_queue.get()
            if data is None:  # Exit signal
                break

            frequency_data, phase_data, step_data = data

            # Clear any existing plots and create a new figure
            plt.clf()
            fig = plt.figure(figsize=(8, 8))

            # Create scatter plot
            plt.scatter(frequency_data,
                        phase_data,
                        c=step_data,
                        cmap='viridis',
                        marker='o',
                        s=100)

            # Add colorbar and labels
            colorbar = plt.colorbar()
            colorbar.set_label('Step Number')
            plt.title('Phase vs Frequency')
            plt.xlabel('Frequency (Hz)')
            plt.ylabel('Phase (rad)')
            plt.grid(True)

            # Instead of saving to file, save to memory buffer
            buf = BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)  # Move to start of buffer

            # Create image from buffer and queue it
            image = Image.open(buf)
            try:
                plot_queue.put_nowait(image.copy())  # Use non-blocking put
                print("Graph image sent to GUI")
            except queue.Full:
                # If queue is full, clear it and add new image
                with plot_queue.mutex:
                    plot_queue.queue.clear()
                plot_queue.put(image.copy())

            # Cleanup
            buf.close()
            plt.close(fig)

        except Exception as e:
            print(f"Error in plotting process: {e}")

class GraphBox:
    def __init__(self, distance):
        self.laser_distance = distance
        # Regular lists for data storage in main thread
        self.amplitude_data = []
        self.phase_data = []
        self.step_data = []
        self.frequency_data = []
        self.diffusivity_estimates = []

        # Create a process-safe queue for plotting
        self.plot_queue = mp.Queue() # Getting data
        self.plot_output = mp.Queue() # Sending finished plots

        # Start the plotting process
        self.plot_process = mp.Process(
            target=plotting_process,
            args=(self.plot_queue, self.plot_output),
            daemon=True
        )
        self.plot_process.start()

    def clear_graph(self):
        """Clear existing graph file and data"""
        # Clear the existing graph file if it exists
        plots_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'plots')
        if os.path.exists(plots_dir):
            temp_file = os.path.join(plots_dir, "temp.png")
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception as e:
                    print(f"Error removing old graph: {e}")

    def update_graph(self, amplitude, phase, step, frequency):
        try:
            # Convert values
            amplitude = float(amplitude)
            phase = float(phase)
            step = int(step)

            # Update data in main thread
            self.amplitude_data.append(amplitude)
            self.phase_data.append(phase)
            self.step_data.append(step)
            self.frequency_data.append(frequency)

            # Send data to plotting process
            self.plot_queue.put((
                self.frequency_data.copy(),
                self.phase_data.copy(),
                self.step_data.copy()
            ))

        except (ValueError, TypeError) as e:
            print(f"Error updating graph data: {e}")
            print(f"Values received: amplitude={amplitude}, phase={phase}, step={step}")

    def instantaneous_diffusivity(self):
        try:
            delta_frequency = abs(self.frequency_data[-1] - self.frequency_data[-2])
        except IndexError:
            delta_frequency = 1
        delta_x = self.laser_distance * float(np.sqrt(np.pi * delta_frequency))
        try:
            delta_y = self.phase_data[-1] - self.phase_data[-2]
        except IndexError:
            delta_y = 1
        slope = delta_y / delta_x
        print(1 / slope ** 2)
        return (1 / slope ** 2) * 1000000

    def __del__(self):
        # Cleanup: send exit signal to plotting process
        if hasattr(self, 'plot_queue'):
            self.plot_queue.put(None)
        if hasattr(self, 'plot_process'):
            self.plot_process.join(timeout=1.0)
            if self.plot_process.is_alive():
                self.plot_process.terminate()