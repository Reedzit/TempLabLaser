import multiprocessing as mp
import queue
import os
from io import BytesIO
import pandas
import sys
from multiprocessing.queues import Queue
from matplotlib import pyplot as plt
import numpy as np
from PIL import Image

def standard_graph(data_queue, plot_queue):
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
            print(f"Error in standard plotting process: {e}")


def candlestick_graph(data_queue, plot_queue):
    while True:
        try:
            file_location = data_queue.get()
            print(f"Candlestick graph received file location: {file_location}")

            if file_location is None:
                print("Received exit signal")
                break  # Exit signal

            # Clear any existing plots and create a new figure
            plt.clf()
            fig = plt.figure(figsize=(8, 8))

            print(f"Attempting to read pickle file from: {file_location}")
            data = pandas.read_pickle(file_location)
            print(f"Successfully read pickle file. Data columns: {data.columns}")

            grouped = data.groupby('FrequencyIn')['PhaseOut']
            mean_phase = grouped.mean()
            std_phase = grouped.std()

            frequencies = mean_phase.index

            plt.errorbar(frequencies, mean_phase, yerr=std_phase, fmt='o')
            plt.title('Phase vs Frequency (Error bars)')
            plt.xlabel('Frequency (Hz)')
            plt.ylabel('Phase (rad)')
            plt.grid(True)

            print("Saving plot to buffer...")
            buf = BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)

            print("Creating image from buffer...")
            image = Image.open(buf)
            print("Attempting to put image in queue...")
            plot_queue.put_nowait(image.copy())
            print("Successfully queued new image")

            buf.close()
            plt.close(fig)

        except Exception as e:
            print(f"Error in candlestick plotting process: {e}")
            print(f"Error type: {type(e)}")
            import traceback
            print(traceback.format_exc())


def plotting_process(data_queue, plot_queue, plot_code = "Default"):
    """Separate process function for plotting"""
    print("Starting plotting process")
    print(f"Plot code Type: {type(plot_code)}")
    print(f"Plot code: {plot_code}")
    if plot_code == "Default":
        standard_graph(data_queue, plot_queue)
    elif plot_code == "Candlestick":
        candlestick_graph(data_queue, plot_queue)
    else:
        print("Invalid plot code")


class GraphBox:
    def __init__(self, distance, plot_code):
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
            args=(self.plot_queue, self.plot_output, plot_code),
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

    def update_graph(self, *args):
        if len(args) == 4:  # Standard graph case with (amplitude, phase, step, frequency)
            amplitude, phase, step, frequency = args
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
        elif len(args) == 1:  # Candlestick case with pickled data file location
            file_location = args[0]
            print(f"Sending pickled data location to plotter: {file_location}")
            self.plot_queue.put(file_location)
        else:
            print(f"Invalid number of arguments received: {len(args)}")


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