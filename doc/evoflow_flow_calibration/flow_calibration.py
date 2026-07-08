from pathlib import Path
import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# -----------------------------
# Settings
# -----------------------------
folder_name = "pump1"

# -----------------------------
# Find the data file in the folder
# -----------------------------

DATA_FOLDER = Path(__file__).parent / folder_name
INPUT_FILE = list(DATA_FOLDER.glob("*.txt"))

rpm_values = []
integrated_flows = []

for file in INPUT_FILE:
    # print(f"Input file: {file}")

    # find pump information
    match = re.search(r"Pump_(\d+)_(\d+)rpm", file.stem)
    if not match:
        print(f"Could not find pump information in file name: {file.stem}")
        continue
    pump_x = match.group(1)
    rpm = match.group(2)

    # extract the data from the file
    data = pd.read_csv(file, sep="\t", encoding="cp1252")
    flow = data["Flow_1(Read)[µl/min]"]
    time = data["Time [s]"]

    # sampling time
    dt = time.diff().mean()
    
    # integrate flow rate to get flow per min
    integrated_flow = 0
    for i in range(len(flow)-1):
        integrated_flow += flow.iloc[i] * dt/60

    # print(f"Pump {pump_x} at {rpm} rpm: Integrated flow = {integrated_flow:.2f} µl/min")

    # take the mean of the flow rate as the average flow rate
    # average_flow = flow.mean()
    # print(f"Pump {pump_x} at {rpm} rpm: Average flow = {average_flow:.2f} µl/min")

    rpm_values.append(int(rpm))
    integrated_flows.append(integrated_flow)

# -----------------------------

# Fit least squares polynomial to the data
coefficients = np.polyfit(rpm_values, integrated_flows, 2)

# Generate a range of rpm values for plotting the fitted curve
rpm_range = np.linspace(min(rpm_values), max(rpm_values), 100)
fitted_flows = np.polyval(coefficients, rpm_range)

# plot the data and the fitted curve
plt.close('all')
fig, ax = plt.subplots()
ax.scatter(rpm_values, integrated_flows, color='blue', label='Data Points')
ax.plot(rpm_range, fitted_flows, color='red', label='Fitted Curve')
ax.set_title(f'Flow Calibration for Pump {pump_x}')
ax.set_xlabel('RPM')
ax.set_ylabel('Integrated Flow (µl/min)')
ax.legend()
ax.grid(True)
fig.tight_layout()
plt.show()
plt.close(fig)
