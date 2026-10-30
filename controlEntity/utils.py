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
        self.config = self._read_settings_file()
        self._flow_rate_pump_1_list, self._flow_rate_pump_2_list, self._flow_rate_pump_3_list, self._flow_rate_pump_4_list = self.extract_flow_conversion_factors(
                    self.config.get("flowRateConversionFactors", "pump_1"),
                    self.config.get("flowRateConversionFactors", "pump_2"),
                    self.config.get("flowRateConversionFactors", "pump_3"),
                    self.config.get("flowRateConversionFactors", "pump_4"),
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
        """Convert RPM to uL/min by inverting the configured RPM(flow) fit."""
        if pump_number == 1:
            a, b, c = self._flow_rate_pump_1_list
        elif pump_number == 2:
            a, b, c = self._flow_rate_pump_2_list
        elif pump_number == 3:
            a, b, c = self._flow_rate_pump_3_list
        elif pump_number == 4:
            a, b, c = self._flow_rate_pump_4_list
        else:
            raise ValueError("Invalid pump number. Must be 1, 2, 3, or 4.")

        rpm_magnitude = abs(rpm)
        if rpm_magnitude == 0.0:
            return 0.0

        roots = np.roots([a, b, c - rpm_magnitude])
        real_roots = roots[np.isreal(roots)].real
        valid_roots = real_roots[real_roots >= 0.0]
        if len(valid_roots) == 0:
            raise ValueError(f"No non-negative flow solution for pump {pump_number} at {rpm} RPM.")

        flow_magnitude = float(valid_roots[np.argmin(valid_roots)])
        return flow_magnitude if rpm > 0.0 else -flow_magnitude

    # Legacy calibration implementation, for coefficients fitted as Flow = f(RPM):
    # def rpm_to_ul_per_min(self, pump_number: int, rpm: float) -> float:
    #     """Convert RPM to uL/min using the former Flow(RPM) polynomial fit."""
    #     if pump_number == 1:
    #         coefficients = self._flow_rate_pump_1_list
    #     elif pump_number == 2:
    #         coefficients = self._flow_rate_pump_2_list
    #     elif pump_number == 3:
    #         coefficients = self._flow_rate_pump_3_list
    #     elif pump_number == 4:
    #         coefficients = self._flow_rate_pump_4_list
    #     else:
    #         raise ValueError("Invalid pump number. Must be 1, 2, 3, or 4.")
    #     flow = coefficients[0] * rpm**2 + coefficients[1] * rpm + coefficients[2]
    #     return 0.0 if flow <= coefficients[2] * 1.1 else flow

    def ul_per_min_to_rpm(self, pump_number: int, ul_per_min: float) -> float:
        """Convert uL/min to RPM using the configured RPM(flow) polynomial fit."""
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

        rpm_magnitude = max(0.0, a * flow_magnitude**2 + b * flow_magnitude + c)
        return rpm_magnitude if ul_per_min > 0 else -rpm_magnitude

    # Legacy inverse implementation, for coefficients fitted as Flow = f(RPM):
    # def ul_per_min_to_rpm(self, pump_number: int, ul_per_min: float) -> float:
    #     """Convert uL/min to RPM by solving the former Flow(RPM) polynomial."""
    #     flow_magnitude = abs(ul_per_min)
    #     if pump_number == 1:
    #         a, b, c = self._flow_rate_pump_1_list
    #     elif pump_number == 2:
    #         a, b, c = self._flow_rate_pump_2_list
    #     elif pump_number == 3:
    #         a, b, c = self._flow_rate_pump_3_list
    #     elif pump_number == 4:
    #         a, b, c = self._flow_rate_pump_4_list
    #     else:
    #         raise ValueError("Invalid pump number. Must be 1, 2, 3, or 4.")
    #     if flow_magnitude <= c * 1.1:
    #         return 0.0
    #     roots = np.roots([a, b, c - flow_magnitude])
    #     real_roots = roots[np.isreal(roots)].real
    #     valid_roots = real_roots[(real_roots >= 0.0) & (real_roots <= 120.0)]
    #     if len(valid_roots) == 0:
    #         raise ValueError("No valid RPM solution for the requested flow.")
    #     rpm_magnitude = float(valid_roots[np.argmin(np.abs(valid_roots))])
    #     return rpm_magnitude if ul_per_min > 0 else -rpm_magnitude

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

    def return_pos_sample_extraction(self, row: int, col: int) -> str:
            pos_dict = {
                        "A1": (0,0),"B1": (1,0),"C1": (2,0),"D1": (3,0),"E1": (4,0),"F1": (5,0),"G1": (6,0),"H1": (7,0),
                        "A2": (0,1),"B2": (1,1),"C2": (2,1),"D2": (3,1),"E2": (4,1),"F2": (5,1),"G2": (6,1),"H2": (7,1),
                        "A3": (0,2),"B3": (1,2),"C3": (2,2),"D3": (3,2),"E3": (4,2),"F3": (5,2),"G3": (6,2),"H3": (7,2),
                        "A4": (0,3),"B4": (1,3),"C4": (2,3),"D4": (3,3),"E4": (4,3),"F4": (5,3),"G4": (6,3),"H4": (7,3),
                        "A5": (0,4),"B5": (1,4),"C5": (2,4),"D5": (3,4),"E5": (4,4),"F5": (5,4),"G5": (6,4),"H5": (7,4),
                        "A6": (0,5),"B6": (1,5),"C6": (2,5),"D6": (3,5),"E6": (4,5),"F6": (5,5),"G6": (6,5),"H6": (7,5),
                        "A7": (0,6),"B7": (1,6),"C7": (2,6),"D7": (3,6),"E7": (4,6),"F7": (5,6),"G7": (6,6),"H7": (7,6),
                        "A8": (0,7),"B8": (1,7),"C8": (2,7),"D8": (3,7),"E8": (4,7),"F8": (5,7),"G8": (6,7),"H8": (7,7),
                        "A9": (0,8),"B9": (1,8),"C9": (2,8),"D9": (3,8),"E9": (4,8),"F9": (5,8),"G9": (6,8),"H9": (7,8),
                        "A10": (0,9),"B10": (1,9),"C10": (2,9),"D10": (3,9),"E10": (4,9),"F10": (5,9),"G10": (6,9),"H10": (7,9),
                        "A11": (0,10),"B11": (1,10),"C11": (2,10),"D11": (3,10),"E11": (4,10),"F11": (5,10),"G11": (6,10),"H11": (7,10),
                        "A12": (0,11),"B12": (1,11),"C12": (2,11),"D12": (3,11),"E12": (4,11),"F12": (5,11),"G12": (6,11),"H12": (7,11),
                        "Waste": (255, 255), "Change Tray": (254, 254), "Change Waste": (253, 253), "Homing": (252, 252),
                    }
            for key, value in pos_dict.items():
                if value == (row, col):
                    return key
            return "Invalid position"

    def return_row_col_sample_extraction(self, pos: str) -> tuple[int, int]:
            pos_dict = {
                        "A1": (0,0),"B1": (1,0),"C1": (2,0),"D1": (3,0),"E1": (4,0),"F1": (5,0),"G1": (6,0),"H1": (7,0),
                        "A2": (0,1),"B2": (1,1),"C2": (2,1),"D2": (3,1),"E2": (4,1),"F2": (5,1),"G2": (6,1),"H2": (7,1),
                        "A3": (0,2),"B3": (1,2),"C3": (2,2),"D3": (3,2),"E3": (4,2),"F3": (5,2),"G3": (6,2),"H3": (7,2),
                        "A4": (0,3),"B4": (1,3),"C4": (2,3),"D4": (3,3),"E4": (4,3),"F4": (5,3),"G4": (6,3),"H4": (7,3),
                        "A5": (0,4),"B5": (1,4),"C5": (2,4),"D5": (3,4),"E5": (4,4),"F5": (5,4),"G5": (6,4),"H5": (7,4),
                        "A6": (0,5),"B6": (1,5),"C6": (2,5),"D6": (3,5),"E6": (4,5),"F6": (5,5),"G6": (6,5),"H6": (7,5),
                        "A7": (0,6),"B7": (1,6),"C7": (2,6),"D7": (3,6),"E7": (4,6),"F7": (5,6),"G7": (6,6),"H7": (7,6),
                        "A8": (0,7),"B8": (1,7),"C8": (2,7),"D8": (3,7),"E8": (4,7),"F8": (5,7),"G8": (6,7),"H8": (7,7),
                        "A9": (0,8),"B9": (1,8),"C9": (2,8),"D9": (3,8),"E9": (4,8),"F9": (5,8),"G9": (6,8),"H9": (7,8),
                        "A10": (0,9),"B10": (1,9),"C10": (2,9),"D10": (3,9),"E10": (4,9),"F10": (5,9),"G10": (6,9),"H10": (7,9),
                        "A11": (0,10),"B11": (1,10),"C11": (2,10),"D11": (3,10),"E11": (4,10),"F11": (5,10),"G11": (6,10),"H11": (7,10),
                        "A12": (0,11),"B12": (1,11),"C12": (2,11),"D12": (3,11),"E12": (4,11),"F12": (5,11),"G12": (6,11),"H12": (7,11),
                        "Waste": (255, 255), "Change Tray": (254, 254), "Change Waste": (253, 253), "Homing": (252, 252),
                    }
            for key, value in pos_dict.items():
                if key == pos:
                    return value
            return "Invalid position"