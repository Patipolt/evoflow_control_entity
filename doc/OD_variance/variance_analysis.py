import pandas as pd
import matplotlib.pyplot as plt

filename = "logs/evoflow_telemetry_od_variance_20260916_150138/evoflow_telemetry_od_variance_20260916_150138_export.csv"

data = pd.read_csv(filename, sep=",")
od = data["od_bioreactor_value"]
time = (data["ts_unix_ms"] - data["ts_unix_ms"].iloc[0]) / 1000.0  # seconds since start

mean = od.mean()
variance = od.var()
std = od.std()

print("OD summary statistics:")
print(od.describe())
print(f"\nVariance: {variance:.6f}")
print(f"Std dev:  {std:.6f}")

fig, ax = plt.subplots(figsize=(12, 5))
ax.plot(time, od, label="OD", color="green")
ax.axhline(mean, color="black", linestyle="--", linewidth=1, label=f"Mean = {mean:.3f}")
ax.fill_between(
    time,
    mean - std,
    mean + std,
    color="green",
    alpha=0.2,
    label=f"±1 std = {std:.3f}",
)
ax.set_xlabel("Time [s]")
ax.set_ylabel("OD [units]")
ax.set_title(f"OD Over Time (variance = {variance:.4f})")
ax.legend()

plt.tight_layout()
plt.savefig("od_variance_analysis.png", dpi=150)
plt.show()