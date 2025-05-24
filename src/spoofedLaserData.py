import math
import random
import time

def spoof_laser_data(freq, time_since_last_measurement):
    # This error factor should be tweaked, but ideally it will converge to 0 over time, and
    # also faster at higher frequencies
    error_factor = random.uniform(-0.5, 0.5) * (1/(time_since_last_measurement*20+1))
    theoretical_value =  35 - (21.6404*math.log(freq))

    spoofed_value = theoretical_value + error_factor*theoretical_value
    print(f"Spoofed value: {spoofed_value}")
    time.sleep(0.1) # This is roughly the time it takes to read the laser data from the instrument
    return spoofed_value