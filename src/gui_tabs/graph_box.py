from matplotlib import pyplot as plt
import matplotlib.cm as cm
import numpy as np
from PIL import Image
import queue
import sys
import os

# TODO: Change the graph to plot:
# Phase of LIA (1) vs Frequency of the laser(2) vs Diffusivity(4)
# Equation thing should output: derivative of: (-(distance between of lasers(user inputed)) * sqrt(pi*freq_laser/diffusivity(what we care about)) = Delta_phase (green vs red))
# X axis: spot distance*sqrt(pi*freq_laser) Spot distance doesn't really change, so this really just a linear product of frequency
# Y axis: Phase of LIA (Lock in amplifier) The phase is going to be changing only as a function of the frequency.
# Find the slope of that graph (Probably the best move here is to estimate it.)
# 1/slope^2 = Diffusivity (what we care about)

# TODO: add signal verification to automation. It should be able to tell if the amplitude is high enough. It should read about 200 mV

# ISSUE: The phase adjustment is not working properly. But we don't need it.
class GraphBox:
    def __init__(self, distance):
        self.laser_distance = distance
        self.image_queue = queue.LifoQueue(maxsize=2)
        self.amplitude_data = []
        self.phase_data = []
        self.step_data = []
        self.frequency_data = []
        self.diffusivity_estimates = []

    def draw_graph(self):
        try:
            plt.clf()  # Clear the current figure
            fig = plt.figure(figsize=(8, 8))

            # Create scatter plot with color representing step number
            scatter = plt.scatter(self.phase_data,  # x-axis: phase
                                  self.amplitude_data,  # y-axis: amplitude
                                  c=self.step_data,  # color based on step number
                                  cmap='viridis',  # color map
                                  marker='o',  # marker style
                                  s=100)  # marker size
            frequency_delta = self.frequency_data[-1] - self.frequency_data[-2]
            barplot = plt.bar()

            # Add colorbar
            colorbar = plt.colorbar(scatter)
            colorbar.set_label('Step Number')

            # Set labels and title
            plt.title('Phase vs Frequency')
            plt.xlabel('Frequency (Hz)')
            plt.ylabel('Phase (rad)')
            plt.grid(True)


            # Save the figure
            plots_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'plots')
            if not os.path.exists(plots_dir):
                os.makedirs(plots_dir)

            image_path = os.path.join(plots_dir, "temp.png")
            plt.savefig(image_path, dpi=100, bbox_inches='tight')
            plt.close('all')  # Close all figures to free memory

        except Exception as e:
            print(f"Error in draw_graph: {e}")
            import traceback
            traceback.print_exc()

    def instantaneous_diffusivity(self):
        # I'm not totally sure where all of these variables are going to come from, but we'll need all of them.
        delta_phase = self.phase_data[-1] - self.phase_data[-2]
        delta_x = self.laser_distance * np.sqrt(np.pi * delta_phase)
        delta_y = self.frequency_data[-1] - self.frequency_data[-2]  # This is the same as the change in frequency
        slope = delta_y / delta_x
        return 1 / slope ** 2  # In theory this should be a good instantaneous estimate

    def update_graph(self, amplitude, phase, step, frequency):
        try:
            # Convert string values to float
            amplitude = float(amplitude)
            phase = float(phase)
            step = int(step)

            # Append new data
            self.amplitude_data.append(amplitude)
            self.phase_data.append(phase)
            self.step_data.append(step)
            self.frequency_data.append(frequency)
            self.diffusivity_estimates.append(self.instantaneous_diffusivity())

            # Draw and save the updated graph
            self.draw_graph()

        except (ValueError, TypeError) as e:
            print(f"Error updating graph data: {e}")
            print(f"Values received: amplitude={amplitude}, phase={phase}, step={step}")

    def queue_image(self):
        image = Image.open(os.path.join(sys.path[0], "temp.png"), "w")
        try:
            self.image_queue.put_nowait(image)
            return True
        except queue.Full:
            print("Queue is full, skipping image")
            return False

