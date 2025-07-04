import multiprocessing as mp
import queue
import os
from io import BytesIO
import pandas
from matplotlib import pyplot as plt
import numpy as np
from PIL import Image

PICKLE_FILE_LOCATION = "./temp"


def standard_graph(data_queue, plot_queue):
    while True:
        try:
            if data_queue.empty():
                continue

            file_location = data_queue.get()
            print(f"Standard graph received file location: {file_location}")

            if file_location is None:
                print("Received exit signal")
                break

            spacing_type = file_location.split("_")[-1].split(".")[0]
            print(f"Detected spacing type: {spacing_type}")

            try:
                data = pandas.read_pickle(file_location)
                print(f"Successfully read data with columns: {data.columns}")
            except Exception as e:
                print(f"Error reading pickle file: {e}")
                continue

            plt.clf()
            fig = plt.figure(figsize=(8, 8))
            ax1 = fig.gca()
            ax2 = ax1.twinx()

            # Plot phase measurements on left axis
            last_measurements = data.groupby('FrequencyIn').last()
            last_scatter = ax1.scatter(last_measurements.index,
                                     last_measurements['PhaseOut'],
                                     marker='o',
                                     s=100,
                                     c='Red',
                                     alpha=0.75)

            average_frequencies = data.groupby('FrequencyIn')
            mean_phases = average_frequencies['PhaseOut'].mean()
            mean_scatter = ax1.scatter(mean_phases.index,
                                     mean_phases,
                                     marker='o',
                                     s=100,
                                     c='Blue',
                                     alpha=0.5)

            # Plot diffusivity on right axis
            filtered_data = data[data['DiffusivityEstimate'].apply(lambda x: isinstance(x, float) and not np.isnan(x))]
            if not filtered_data.empty:
                diff_data = filtered_data.groupby('FrequencyIn')['DiffusivityEstimate'].last()
                barGraph = ax2.bar(diff_data.index, 
                                 diff_data.values, 
                                 alpha=0.3,
                                 color='green',
                                 zorder=2,
                                 width=(ax1.get_xlim()[1] - ax1.get_xlim()[0])*(1/(len(diff_data)+1)))
                
                # Combine legends from both axes
                ax1.legend([last_scatter, mean_scatter, barGraph], 
                         ['Most Recent Phase', 'Average Phase', 'Diffusivity Estimate'])
            else:
                ax1.legend([last_scatter, mean_scatter], 
                         ['Most Recent Phase', 'Average Phase'])

            # Set labels
            ax1.set_xlabel('Frequency (Hz)')
            ax1.set_ylabel('Phase (rad)', color='blue')
            ax2.set_ylabel('Diffusivity', color='green')

            # Set scales
            if spacing_type == "logspace":
                ax1.set_xscale('log')

            plt.title('Phase and Diffusivity vs Frequency')
            ax1.grid(True)

            # Adjust colors of tick labels to match their data
            ax1.tick_params(axis='y', labelcolor='blue')
            ax2.tick_params(axis='y', labelcolor='green')

            plt.tight_layout()

            buf = BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)

            image = Image.open(buf)
            plot_queue.put_nowait(image.copy())

            buf.close()
            plt.close(fig)

        except Exception as e:
            print(f"Error in plotting process: {e}")
            print(traceback.format_exc())


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

            if 'Convergence' in data.columns:
                converged_data = data[data['Convergence'] == True]
                if len(converged_data) == 0:
                    print("No converged data points found")
                    continue
            else:
                print("No convergence data found in dataset")
                converged_data = data

            grouped = converged_data.groupby('FrequencyIn')['PhaseOut']
            mean_phase = grouped.mean()
            std_phase = grouped.std()

            frequencies = mean_phase.index

            sample_size = grouped.count()

            plt.errorbar(frequencies, mean_phase, yerr=std_phase, fmt='none')

            # Plot colored points with sample size mapped to color
            sc = plt.scatter(frequencies, mean_phase, c=sample_size, cmap='gist_rainbow', zorder=2)
            plt.colorbar(sc, label='Sample Size')

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
        self.PICKLE_FILE_LOCATION = PICKLE_FILE_LOCATION
        self.laser_distance = distance
        # Regular lists for data storage in main thread
        self.amplitude_data = []
        self.phase_data = []
        self.step_data = []
        self.frequency_data = []
        self.diffusivity_estimates = []

        # Create a process-safe queue for plotting
        self.data_queue = mp.Queue() # Getting data
        self.plot_output = mp.Queue() # Sending finished plots

        # Start the plotting process
        self.plot_process = mp.Process(
            target=plotting_process,
            args=(self.data_queue, self.plot_output, plot_code),
            daemon=True
        )
        self.plot_process.start()

    def close_plotting_process(self):
        """Close the plotting process"""
        self.data_queue.put(None)

    @staticmethod
    def clear_graph():
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

    def update_graph(self, data):
        print(f"Sending pickled data location to plotter: {PICKLE_FILE_LOCATION}")
        # Send pickled data location to plotting process
        pandas.to_pickle(data, PICKLE_FILE_LOCATION)
        self.data_queue.put(PICKLE_FILE_LOCATION)


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
        if hasattr(self, 'data_queue'):
            self.data_queue.put(None)
        if hasattr(self, 'plot_process'):
            self.plot_process.join(timeout=1.0)
            if self.plot_process.is_alive():
                self.plot_process.terminate()