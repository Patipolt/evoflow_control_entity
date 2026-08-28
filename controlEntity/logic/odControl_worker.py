"""
OD Control Worker

This module defines the ODControlWorker class, which manages the OD control logic for the EvoFlow system. It interfaces with the ODControl device to regulate optical density (OD) in bioreactors and lagoons.
The worker runs in a separate thread, allowing for asynchronous control operations and communication with the EvoFlow device.

Project: EvoFlow Innosuisse
Author: Patipol Thanuphol, Scientific Researcher at ZHAW — thau @zhaw.ch | patipol.thanu@gmail.com
Created: April 2026
"""

from PySide6.QtCore import QObject, QTimer, Signal, Slot
from evoflow.device.odControl import ODControl


class ODControlWorker(QObject):
    """Worker class to manage OD control logic in a separate thread."""
    
    # Signal to emit the computed inlet flow rate (q_in) for the bioreactor
    q_in_updated = Signal(float)
    q_waste_updated = Signal(float)
    q_lagoon_updated = Signal(float)
    estimated_od_updated = Signal(float)
    
    def __init__(self, V0: float, A0: float, mu0: float, kp: float, ki: float, q_max: float, Ts: float, A_setpoint: float):
        super().__init__()
        self.od_control = ODControl(V0, A0, mu0, kp, ki, q_max, Ts, A_setpoint)
        self.estimated_od = None
        self.q_in = None
        self.q_waste = None
        self.q_lagoon = 0.05    # hardcoded for testing
        self.first_run =True
        self._control_timer = QTimer(self)
        self._control_timer.timeout.connect(self.run_control_loop)

    @Slot(bool)
    def set_od_control_enabled(self, enabled: bool):
        """Enable or disable the OD control loop."""
        if enabled:
            print("OD Control Loop started.")
            self.start()
        else:
            self.stop()

    @Slot()
    def start(self):
        """Start the OD control loop."""
        self._control_timer.start(self.od_control.Ts * 1000)  # Convert Ts to milliseconds

    @Slot()
    def stop(self):
        """Stop the OD control loop."""
        self._control_timer.stop()
        self.clear_control_state()

    @Slot(float)
    def calculate_dilution_flow(self, current_od: float) -> float:
        """Calculate the required inlet flow rate (q_in) based on the current OD measurement."""
        self.q_in = self.od_control.calculate_dilution_flow(current_od)
        return self.q_in

    @Slot(float)
    def estimate_growth_rate(self, current_od: float) -> float:
        """Estimate the bacterial growth rate based on the current OD measurement."""
        return self.od_control.estimate_growth_rate(current_od)

    @Slot(float)
    def calculate_outlet_flows(self, preferred_q_lagoon: float) -> tuple:
        """Calculate the required outlet flow rates (q_waste, q_lagoon) based on the preferred lagoon flow rate."""
        self.q_waste, self.q_lagoon = self.od_control.calculate_outlet_flows(preferred_q_lagoon)
        return self.q_waste, self.q_lagoon

    @Slot(float)
    def estimate_od(self, current_od: float) -> float:
        """Estimate the next OD based on the current OD, estimated growth rate, and inlet flow rate."""
        self.estimated_od = self.od_control.estimate_od(current_od)
        return self.estimated_od

    @Slot()
    def clear_control_state(self):
        """Reset the internal state of the controller."""
        self.od_control.clear_control_state()
        self.estimated_od = None
        self.q_in = None
        self.q_waste = None
        self.first_run = True

    def run_control_loop(self):
        """Update the current OD measurement and compute the new inlet flow rate."""
        if self.first_run:
            q_in = self.calculate_dilution_flow(self.od_control.A0)
            self.estimated_od = self.estimate_od(self.od_control.A0)
            self.first_run = False
        else:
            q_in = self.calculate_dilution_flow(self.estimated_od)
            self.estimated_od = self.estimate_od(self.estimated_od)

        self.q_waste, self.q_lagoon = self.calculate_outlet_flows(self.q_lagoon if self.q_lagoon is not None else 0.0)
        
        self.q_in_updated.emit(q_in)
        self.q_waste_updated.emit(self.q_waste)
        self.q_lagoon_updated.emit(self.q_lagoon)
        self.estimated_od_updated.emit(self.estimated_od)
        print(f"OD Control Loop: Estimated OD={self.estimated_od:.3f}, q_in={q_in:.3f}, q_waste={self.q_waste:.3f}, q_lagoon={self.q_lagoon:.3f}")
