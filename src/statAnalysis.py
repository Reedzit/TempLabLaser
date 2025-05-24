import numpy as np
import pandas as pd

# This is written as a package of standalone functions

# Constants for convergence check
THRESHOLD_STD = 0.01
NUM_SAMPLES = 30
# This should check for convergence of the data. It needs to read data and return if the data has converged.
def check_for_convergence(data, index):
    data_std = np.std(data[index].tail(NUM_SAMPLES))
    if data_std < THRESHOLD_STD:
        print(f"Data converged. Standard deviation: {data_std}")
        return True
    else:
        print(f"Data not converged. Standard deviation: {data_std}")
        return False

def calculate_error_bounds(data, index):
    data_std = np.std(data[index].tail(NUM_SAMPLES))
    data_mean = np.mean(data[index].tail(NUM_SAMPLES))
    return data_mean - data_std, data_mean + data_std