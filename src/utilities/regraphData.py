import pandas as pd
import numpy as np

import matplotlib.pyplot as plt

# Read data from Excel file
data = pd.read_csv("C:\\Users\\templab\Desktop\\Seth\Data Collection\\10-27-2025\\measurement_data_2025-10-27_15-29-39 (0,0).csv")

# Create the plot
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

# Calculate and plot mean phases
average_frequencies = data.groupby('FrequencyIn')
mean_phases = average_frequencies['PhaseOut'].mean()
mean_scatter = ax1.scatter(mean_phases.index,
                         mean_phases,
                         marker='o',
                         s=100,
                         c='Blue',
                         alpha=0.5)

# Plot diffusivity on right axis (uncomment if you have diffusivity data)

# Set labels and styling
ax1.set_xlabel('Frequency (Hz)')
ax1.set_ylabel('Phase (rad)', color='blue')
ax2.set_ylabel('Diffusivity', color='green')

# Set log scale if needed (uncomment if required)
ax1.set_xscale('log')

plt.title('Phase and Diffusivity vs Frequency')
ax1.grid(True)

# Adjust colors of tick labels
ax1.tick_params(axis='y', labelcolor='blue')
ax2.tick_params(axis='y', labelcolor='green')

plt.tight_layout()
plt.show()