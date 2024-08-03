import pandas as pd
from datetime import datetime
import sys

def pxx(percentile, data):
    """
    Calculate the given percentile of a dataset.
    
    :param percentile: The percentile to calculate (e.g., 90 for P90).
    :param data: A list of data points.
    :return: The value at the given percentile.
    """
    if not 0 <= percentile <= 100:
        raise ValueError("Percentile must be between 0 and 100")
    
    if not data:
        raise ValueError("Data list cannot be empty")
    
    # Sort the data
    sorted_data = sorted(data)
    N = len(sorted_data)
    
    # Calculate the rank
    rank = percentile / 100 * (N - 1)
    
    # If the rank is an integer, return the corresponding value
    if rank.is_integer():
        return sorted_data[int(rank)]
    
    # Otherwise, interpolate between the closest ranks
    lower_rank = int(rank)
    upper_rank = lower_rank + 1
    weight = rank - lower_rank
    
    return sorted_data[lower_rank] * (1 - weight) + sorted_data[upper_rank] * weight

def get_entry_exit_time(file_path, percentile):
    """
    Get entry and exit times from a CSV file and calculate the specified percentile for the hours.
    
    :param file_path: Path to the CSV file.
    :param percentile: The percentile to calculate (e.g., 90 for P90).
    :return: Tuple containing the entry times, exit times, and the calculated percentile hour.
    """
    # Read the CSV file
    df = pd.read_csv(file_path)
    
    # Extract Entry Time and Exit Time columns
    entry_times = df['Entry Time'].tolist()
    exit_times = df['Exit Time'].tolist()
    
    # Parse the date strings and extract the hour
    entry_hours = [datetime.strptime(time, "%Y-%m-%d %H:%M").hour for time in entry_times]
    exit_hours = [datetime.strptime(time, "%Y-%m-%d %H:%M").hour for time in exit_times]
    
    # Calculate the specified percentile for entry and exit hours
    entry_percentile_hour = pxx(percentile, entry_hours)
    exit_percentile_hour = pxx(percentile, exit_hours)
    
    return entry_times, exit_times, entry_percentile_hour, exit_percentile_hour

# Example usage:
file_path = sys.argv[1]  # Replace with the actual path to your CSV file
percentile = 80
entry_times, exit_times, entry_p90, exit_p90 = get_entry_exit_time(file_path, percentile)

print(f"P{percentile} Entry Hour: {entry_p90}")
print(f"P{percentile} Exit Hour: {exit_p90}")
