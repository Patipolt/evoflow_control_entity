"""
Utility functions for the EvoFlow control entity.

Project: EvoFlow Innosuisse
Author: Patipol Thanuphol, Scientific Researcher at ZHAW — thau @zhaw.ch | patipol.thanu@gmail.com
Created: April 2026
"""

import configparser
from pathlib import Path
import sys
import numpy as np

def resource_path(*relative_parts: str) -> Path:
    """
    Resolve a resource path that works in both development and PyInstaller bundles.

    - In a frozen build, PyInstaller unpacks data files under `_MEIPASS/controlEntity` because
      we add data with targets like `controlEntity/assets`.
    - In development, resources live next to this module inside the `controlEntity` package.

    The function accepts one or more path segments (or a single string that can include
    separators). If callers pass a path that is already prefixed with `controlEntity/`, the
    prefix is stripped to avoid duplicating the folder name.
    """

    # Flatten path parts and strip a leading "controlEntity" if present to avoid double nesting
    parts = []
    for part in relative_parts:
        if part:
            parts.extend(Path(part).parts)

    if parts and parts[0] == "controlEntity":
        parts = parts[1:]

    relative_path = Path(*parts)

    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base_path = Path(sys._MEIPASS) / "controlEntity"
    else:
        base_path = Path(__file__).resolve().parent

    return base_path / relative_path

def colored_text(text: str, color: str) -> str:
    """Colorize the given text in the given color"""
    colors = {
        'Red': [255, 0, 0],
        'Green': [0, 255, 0],
        'Blue': [0, 200, 255],
        'Yellow': [255, 255, 0],
        'Orange': [255, 150, 0],
        'Pink': [255, 0, 150],
        'Violet': [200, 100, 200],
        'Pale': [255, 235, 200],
        'reset': '\033[0m'
    }
    if color not in colors:
        raise ValueError(f"Color '{color}' is not supported.")
    return f"\033[38;2;{colors[color][0]};{colors[color][1]};" \
           f"{colors[color][2]}m{text}{colors['reset']}"

HEX_COLOR_LIST = ["0072BD",
                  "D95319",
                  "EDB120",
                  "7E2F8E",
                  "77AC30",
                  "4DBEEE",
                  "A2142F",
                  "0072BD",
                  "D95319",
                  "EDB120",
                  "7E2F8E",
                  "77AC30",
                  "4DBEEE",
                  "A2142F",
                  "0072BD",
                  "D95319",
                  "EDB120",
                  "7E2F8E",
                  "77AC30",
                  "4DBEEE"]

class Utils:
    """Utility class for the EvoFlow control entity"""
    def __init__(self):
        config = self._read_settings_file()
        self._flow_rate_pump_1_list, self._flow_rate_pump_2_list, self._flow_rate_pump_3_list, self._flow_rate_pump_4_list = self.extract_flow_conversion_factors(
                    config.get("flowRateConversionFactors", "pump_1"),
                    config.get("flowRateConversionFactors", "pump_2"),
                    config.get("flowRateConversionFactors", "pump_3"),
                    config.get("flowRateConversionFactors", "pump_4"),
                )
        
    def extract_flow_conversion_factors(self, pump1_str_list: str, pump2_str_list: str, pump3_str_list: str, pump4_str_list: str) -> tuple[list[float], list[float], list[float], list[float]]:
            """Extract flow conversion factors from string lists and store them as floats"""
            try:
                pump1_factors = [float(x) for x in pump1_str_list.split(",") if x.strip()]
                pump2_factors = [float(x) for x in pump2_str_list.split(",") if x.strip()]
                pump3_factors = [float(x) for x in pump3_str_list.split(",") if x.strip()]
                pump4_factors = [float(x) for x in pump4_str_list.split(",") if x.strip()]
    
                return pump1_factors, pump2_factors, pump3_factors, pump4_factors
            except ValueError as e:
                self.status_message.emit(f"Error parsing flow conversion factors: {e}")
                return [], [], [], []

    @staticmethod
    def _read_settings_file() -> configparser.ConfigParser:
        """Load settings from config/settings.ini"""
        config_path = resource_path("config/settings.ini")
        config = configparser.ConfigParser()
        config.read(str(config_path))
        return config

    def rpm_to_ul_per_min(self, pump_number: int, rpm: float) -> float:
        """Convert RPM to ul/min using polynomial fit for the specified pump"""
        if pump_number == 1:
            # Use second order polynomial fit for pump 1
            flow = self._flow_rate_pump_1_list[0]*rpm**2 + self._flow_rate_pump_1_list[1]*rpm + self._flow_rate_pump_1_list[2]
            if flow <= self._flow_rate_pump_1_list[2]*1.1:  # Allow a small tolerance above the minimum flow
                return 0.0
        elif pump_number == 2:
            # Use second order polynomial fit for pump 2
            flow = self._flow_rate_pump_2_list[0]*rpm**2 + self._flow_rate_pump_2_list[1]*rpm + self._flow_rate_pump_2_list[2]
            if flow <= self._flow_rate_pump_2_list[2]*1.1:  # Allow a small tolerance above the minimum flow
                return 0.0
        elif pump_number == 3:
            # Use second order polynomial fit for pump 3
            flow = self._flow_rate_pump_3_list[0]*rpm**2 + self._flow_rate_pump_3_list[1]*rpm + self._flow_rate_pump_3_list[2]
            if flow <= self._flow_rate_pump_3_list[2]*1.1:  # Allow a small tolerance above the minimum flow
                return 0.0
        elif pump_number == 4:
            # Use second order polynomial fit for pump 4
            flow = self._flow_rate_pump_4_list[0]*rpm**2 + self._flow_rate_pump_4_list[1]*rpm + self._flow_rate_pump_4_list[2]
            if flow <= self._flow_rate_pump_4_list[2]*1.1:  # Allow a small tolerance above the minimum flow
                return 0.0
        else:
            raise ValueError("Invalid pump number. Must be 1, 2, 3, or 4.")

        return flow

    def ul_per_min_to_rpm(self, pump_number: int, ul_per_min: float) -> float:
        """Convert uL/min to RPM using polynomial fit for the specified pump"""
        flow_magnitude = abs(ul_per_min)

        if pump_number == 1:
            # Use second order polynomial fit for pump 1
            a, b, c = self._flow_rate_pump_1_list
        elif pump_number == 2:
            # Use second order polynomial fit for pump 2
            a, b, c = self._flow_rate_pump_2_list
        elif pump_number == 3:
            # Use second order polynomial fit for pump 3
            a, b, c = self._flow_rate_pump_3_list
        elif pump_number == 4:
            # Use second order polynomial fit for pump 4
            a, b, c = self._flow_rate_pump_4_list
        else:
            raise ValueError("Invalid pump number. Must be 1, 2, 3, or 4.")

        # check for the dead band of the pump, if the flow magnitude is less than the minimum flow, return 0 RPM
        min_flow = c  # The constant term represents the minimum flow at 0 RPM
        if flow_magnitude <= min_flow*1.1:  # Allow a small tolerance above the minimum flow
            return 0.0

        # Use the fitted forward-direction curve to get RPM magnitude, then apply the requested flow sign.
        coeffs = [a, b, c - flow_magnitude]
        roots = np.roots(coeffs)
        real_roots = roots[np.isreal(roots)].real

        if len(real_roots) == 0:
            raise ValueError("No real solution found for the given uL/min value.")

        # Keep only physically valid positive RPM magnitudes; reverse direction is applied afterward.
        rpm_abs_max = 300.0
        valid_roots = real_roots[(real_roots >= 0.0) & (real_roots <= rpm_abs_max)]

        if len(valid_roots) == 0:
            raise ValueError(
                f"No valid RPM magnitude solution in [0.0, {rpm_abs_max}] for pump {pump_number} and flow {ul_per_min} uL/min."
            )

        rpm_magnitude = float(valid_roots[np.argmin(np.abs(valid_roots))])
        return rpm_magnitude if ul_per_min > 0 else -rpm_magnitude

    def rpm_to_ul_per_sec(self, pump_number: int, rpm: float) -> float:
            """Convert RPM to ul/sec using polynomial fit for the specified pump"""
            ul_per_min = self.rpm_to_ul_per_min(pump_number, rpm)
            return ul_per_min / 60.0

    def ul_per_sec_to_rpm(self, pump_number: int, ul_per_sec: float) -> float:
                """Convert ul/sec to RPM using polynomial fit for the specified pump"""
                ul_per_min = ul_per_sec * 60.0
                return self.ul_per_min_to_rpm(pump_number, ul_per_min)

    def rpm_to_ml_per_sec(self, pump_number: int, rpm: float) -> float:
            """Convert RPM to ml/sec using polynomial fit for the specified pump"""
            ul_per_min = self.rpm_to_ul_per_min(pump_number, rpm)
            return ul_per_min / 1000.0 / 60.0

    def ml_per_sec_to_rpm(self, pump_number: int, ml_per_sec: float) -> float:
            """Convert ml/sec to RPM using polynomial fit for the specified pump"""
            ul_per_min = ml_per_sec * 1000.0 * 60.0
            return self.ul_per_min_to_rpm(pump_number, ul_per_min)