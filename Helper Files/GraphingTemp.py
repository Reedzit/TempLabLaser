from matplotlib import pyplot as plt
import pandas as pd

reflectance_map = pd.read_csv(r"C:\Users\templab\Documents\Automation Testing\16Sep2025\SampleMappingTestsample mapping,Stepsize-0.5,Time-2025-09-23 11_24_19.csv")

fig, ax = plt.subplots(subplot_kw={"projection": "3d"})
scat = ax.scatter(reflectance_map['X'], reflectance_map['Y'], c=reflectance_map['Amplitude'], cmap='viridis')
fig.colorbar(scat, ax=ax, label='Amplitude')

ax.set_xlabel('X Position (mm)')
ax.set_ylabel('Y Position (mm)')
ax.set_zlabel('Z Position (mm)')
ax.set_title('3D Reflectance Map')

plt.show()