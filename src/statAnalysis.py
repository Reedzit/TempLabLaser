import numpy as np
import pandas as pd

# This is written as a package of standalone functions

# Constants for convergence check
THRESHOLD_STD_PERCENT = 1
NUM_SAMPLES = 30
# This should check for convergence of the data. It needs to read data and return if the data has converged.
def check_for_convergence(data, index):
    #print(f"\nChecking convergence...")
    #print(f"Total data points: {len(data[index])}")
    if len(data[index]) < NUM_SAMPLES:
        print(f"Not enough samples yet. Have {len(data[index])}, need {NUM_SAMPLES}")
        return False

    last_samples = data[index].tail(NUM_SAMPLES)
    data_std = np.std(last_samples)
    data_mean = np.mean(last_samples)
    #print(f"Last {NUM_SAMPLES} samples:")
    # print(f"Mean: {data_mean:.4f}")
    #print(f"Standard deviation: {data_std/data_mean*100:.4f}% of mean")
    # print(f"Threshold: {THRESHOLD_STD}")

    if data_std/last_samples.mean()*100 < THRESHOLD_STD_PERCENT:
        print("*** CONVERGENCE ACHIEVED ***")
        return True
    else:
        #print("No convergence yet - standard deviation above threshold")
        return False

def calculate_error_bounds(data, index):
    data_std = np.std(data[index].tail(NUM_SAMPLES))
    data_mean = np.mean(data[index].tail(NUM_SAMPLES))
    return data_mean - data_std, data_mean + data_std