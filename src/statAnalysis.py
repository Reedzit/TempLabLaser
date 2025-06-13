import numpy as np
import pandas as pd
from scipy import stats

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
        #print("*** CONVERGENCE ACHIEVED ***")
        return True
    else:
        #print("No convergence yet - standard deviation above threshold")
        return False

def calculate_error_bounds(data, index):
    data_std = np.std(data[index].tail(NUM_SAMPLES))
    data_mean = np.mean(data[index].tail(NUM_SAMPLES))
    return data_mean - data_std, data_mean + data_std
# Constants for diffusivity estimation


def estimate_diffusivity(data_in, spot_distance):
    """
    Estimates diffusivity using frequency and phase measurements.
    The relationship between phase and frequency is logarithmic,
    which needs to be transformed into a linear relationship for diffusivity calculation.
    
    Args:
        data_in: DataFrame with 'FrequencyIn' and 'PhaseOut' columns
        spot_distance

    Returns:
        float: Estimated diffusivity value
    """
    SPOT_DISTANCE = spot_distance
    def construct_diffusivity_graph(data):
        # Create a copy to avoid modifying the original data
        processed_data = data.copy()
        
        # First take log of frequency to linearize the relationship
        # Since the theoretical relationship is: phase = 35 - 21.6404 * log(freq)
        processed_data["FrequencyIn"] = np.log10(processed_data["FrequencyIn"])
        
        # Then apply the transformation for diffusivity calculation
        # X axis becomes: spot_distance * sqrt(pi * log_freq)
        processed_data["FrequencyIn"] = SPOT_DISTANCE * np.sqrt(np.pi * processed_data["FrequencyIn"])
        
        # Group by frequency and take mean of phase values
        grouped_data = processed_data.groupby("FrequencyIn", as_index=False).agg({
            "PhaseOut": "mean"
        })
        
        # Sort by frequency to ensure proper slope calculation
        return grouped_data.sort_values("FrequencyIn")

    def determine_slope(data):
        if len(data) < 2:
            print("Error: Not enough data points for linear regression")
            return None
            
        slope, intercept, r_value, p_value, std_err = stats.linregress(
            data["FrequencyIn"], 
            data["PhaseOut"]
        )
        print(f"Slope: {slope:.4f}")
        print(f"R-value: {r_value:.4f}")
        print(f"Data points used: {len(data)}")
        return slope

    processed_data = construct_diffusivity_graph(data_in)
    slope = determine_slope(processed_data)
    
    if slope is None or slope == 0:
        print("Cannot calculate diffusivity: invalid slope")
        return None
        
    diffusivity_estimate = 1/(slope**2)
    print(f"Diffusivity estimate: {diffusivity_estimate:.4f}")
    return diffusivity_estimate