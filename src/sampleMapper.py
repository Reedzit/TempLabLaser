import numpy as np
import pandas as pd
import threading
import time
import matplotlib.pyplot as plt
plt.switch_backend('TkAgg')

class SampleMapper:
    def __init__(self, hexapod, instruments, thread, imageQueue, settings):
        self.hexapod = hexapod
        self.instruments = instruments


        self.thread = thread
        self.imageQueue = imageQueue

        (self.step_size, self.threshold) = settings # Unpack settings as needed
        self.reflectance_map = pd.DataFrame()
        self.c_r_p = np.array([0.0, 0.0, 0.0]) # Current relative position, the position relative to the starting point

        self.is_running = False
    
    def measurement_stuff(self):
        measurement = self.instruments.take_measurement()
        x, y, z = self.c_r_p[0], self.c_r_p[1], self.c_r_p[2] # unpack current relative position because we're going to convert it to the panda's dataframe
        self.reflectance_map = pd.concat([self.reflectance_map, pd.DataFrame({'X': [x], 'Y': [y], 'Z': [z], 'Measurement': [measurement]})], ignore_index=True)
        # The dataframe has columns X, Y, Z, Measurement. We'll plot this later. But the dataframe should make it easier to save and load data.
        # we can also sort by X and Y to make a grid if needed.
        print(f"Measurement at ({x}, {y}, {z}): {measurement}")


    def find_edge(self, direction):
        direction = np.normalize(direction) # Ensure direction is a unit vector
        step = self.step_size * direction
        if self.hexapod is None:
            print("Hexapod not initialized.")
            return None
        else:
            print(f"Finding edge in {direction} direction...")
        self.measurement_stuff() # Take initial measurement
        if self.reflectance_map.empty:
            print("Reflectance map is empty. Cannot find edge.")
            return None
        elif self.reflectance_map['Measurement'].iloc[-1] < self.threshold:
            print("Initial measurement below threshold. Cannot find edge if we don't start on the sample.")
            return None
        while self.reflectance_map['Measurement'].iloc[-1] >= self.threshold and self.is_running:
            self.hexapod.move_relative(*step) # Not sure if this is the right method name
            self.c_r_p += step
            if self.hexapod.is_moving():
                time.sleep(0.1)


    def start_mapping(self):
        if self.hexapod is None:
            print("Hexapod not initialized.")
            return
        else:
            print("Starting sample mapping...")
            self.is_running = True