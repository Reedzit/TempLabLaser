import math

def spoof_laser_data(freq):
    return 35 - (21.6404*math.log(freq))