import numpy as np
import pandas as pd
import threading
import time
import datetime
import matplotlib.pyplot as plt
plt.switch_backend('TkAgg')

class SampleMapper:
    def __init__(self, hexapod, instruments, imageQueue, settings = (.5, 0.02, None)):
        self.hexapod = hexapod
        self.instruments = instruments

        self.imageQueue = imageQueue

        (self.step_size, self.threshold, self.file_location) = settings # Unpack settings as needed
        self.reflectance_map = pd.DataFrame()
        self.c_r_p = np.array([0.0, 0.0, 0.0]) # Current relative position, the position relative to the starting point

        self.is_running = False
    
    def measurement_stuff(self):
        time.sleep(0.1) # Give some time for the hexapod to settle TODO: implement that bug fix
        measurement = self.instruments.take_measurement()
        x, y, z = self.c_r_p[0], self.c_r_p[1], self.c_r_p[2] # unpack current relative position because we're going to convert it to the panda's dataframe
        self.reflectance_map = pd.concat([self.reflectance_map, pd.DataFrame({'X': [x], 'Y': [y], 'Z': [z], 'Amplitude': [measurement[0]], 'Phase': [measurement[1]]})], ignore_index=True)
        # The dataframe has columns X, Y, Z, Measurement. We'll plot this later. But the dataframe should make it easier to save and load data.
        # we can also sort by X and Y to make a grid if needed.
        print(f"Measurement at ({x}, {y}, {z}): {measurement}")


    def find_edge(self, direction):
        if self.hexapod is None:
            print("Hexapod not initialized.")
            return None
        else:
            print(f"Finding edge in {direction} direction...")
        self.measurement_stuff() # Take initial measurement
        if self.reflectance_map.empty:
            print("Reflectance map is empty. Something is wrong with the instrumentation.")
            return None
        elif self.reflectance_map['Amplitude'].iloc[-1] < self.threshold:
            print("Initial measurement below threshold. Cannot find edge if we don't start on the sample.")
            return None
        direction = direction/np.linalg.norm(direction) # Normalize direction
        print(f"Normalized direction: {direction}")
        while self.reflectance_map['Amplitude'].iloc[-1] >= self.threshold and self.is_running:
            if not self.hexapod.ready_for_commands:
                time.sleep(0.1)
            self.hexapod.translate(direction, magnitude = self.step_size)
            self.c_r_p += direction * self.step_size # Update current relative position
            if not self.hexapod.ready_for_commands:
                time.sleep(0.1)
            self.measurement_stuff()
        print(f"Edge found at position: {self.c_r_p}")
        print("Stepping back to be on the sample...")
        while self.reflectance_map['Amplitude'].iloc[-1] < self.threshold and self.is_running:
            if not self.hexapod.ready_for_commands:
                time.sleep(0.1)
            self.hexapod.translate(-direction, magnitude = self.step_size/10)
            self.c_r_p += direction * self.step_size/10 # Update current relative position
            if not self.hexapod.ready_for_commands:
                time.sleep(0.1)
            self.measurement_stuff()
        print(f"Stepped back to position: {self.c_r_p}")



    def start_mapping(self):
        if self.hexapod is None:
            print("Hexapod not initialized.")
            return
        else:
            print("Starting sample mapping...")
            self.is_running = True
            self.find_edge(np.array([1, 0, 0])) # Find right edge
            self.find_edge(np.array([-1, 0, 0])) # Find left edge
            self.find_edge(np.array([0, 1, 0])) # Find top edge
            self.find_edge(np.array([0, -1, 0])) # Find bottom edge
            self.is_running = False

            if self.file_location is not None:
                print(f"Saving reflectance map to {self.file_location}...")
                self.reflectance_map.to_csv(self.file_location+f"sample mapping,Stepsize-{self.step_size},Time-{datetime.datetime.now().strftime("%Y-%m-%d %H_%M_%S")}.csv", index=False)
            else:
                print("No file location specified, not saving reflectance map.")
            print("Sample mapping complete. LOGIC INCOMPLETE!!")
        
    def debug_mode(self):
        # This is just a debug mode to test the measurement stuff without moving the hexapod
        self.is_running = True
        while True:
            command = input("""
                            Enter command:
                            e - to find edge in a direction
                            m - to try mapping logic
                            s - to print the last thing put into the measurement dataframe
                            q - to quit debug mode
                            """)
            if command == 'e':
                direction_input = input("Enter direction as x,y,z (e.g., 1,0,0 for right): ")
                direction = np.array([float(i) for i in direction_input.split(',')])
                self.find_edge(direction)
            elif command == 'm':
                self.start_mapping()
            elif command == 's':
                if not self.reflectance_map.empty:
                    print(self.reflectance_map.iloc[-1])
                else:
                    print("Reflectance map is empty.")
            elif command == 'q':
                self.is_running = False
                break