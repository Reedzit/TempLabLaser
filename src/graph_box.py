from matplotlib import pyplot as plt
import matplotlib.cm as cm
import numpy as np
from PIL import Image
import queue
import sys
import os


class GraphBox:
    def __init__(self, x, y, z, width, height):
        self.image_queue = queue.LifoQueue(maxsize=2)
        self.amplitude_data = []
        self.phase_data = []
        self.step_data = []

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

            # Add colorbar
            colorbar = plt.colorbar(scatter)
            colorbar.set_label('Step Number')

            # Set labels and title
            plt.title('Amplitude vs Phase')
            plt.xlabel('Phase (degrees)')
            plt.ylabel('Amplitude (V)')
            plt.grid(True)

            plt.tight_layout()

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

    def update_graph(self, amplitude, phase, step):
        try:
            # Convert string values to float
            amplitude = float(amplitude)
            phase = float(phase)
            step = int(step)

            # Append new data
            self.amplitude_data.append(amplitude)
            self.phase_data.append(phase)
            self.step_data.append(step)

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
