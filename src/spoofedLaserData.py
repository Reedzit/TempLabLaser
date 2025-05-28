import math
import random
import time

def spoof_laser_data(freq, time_since_last_measurement):
    #print(f"Received frequency: {freq}, type: {type(freq)}")
    # This error factor should be tweaked, but ideally it will converge to 0 over time, and
    # also faster at higher frequencies
    error_factor = random.uniform(-0.5, 0.5) * (1 / (time_since_last_measurement * 20 + 1))
    #print(f"About to calculate log of frequency: {freq}")
    theoretical_value = 35 - (21.6404 * math.log(freq))
    time.sleep(0.2)
    spoofed_value = theoretical_value + error_factor * theoretical_value
    return spoofed_value