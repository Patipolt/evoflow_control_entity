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
    
    def __init__(self, V0: float, A0: float, mu0: float, kp: float, ki: float, q_max: float, q_lagoon_max: float, Ts: float, A_setpoint: float, anti_windup_limit: float, back_calculation_gain: float):
        super().__init__()
        self.od_control = ODControl(V0, A0, mu0, kp, ki, q_max, q_lagoon_max, Ts, A_setpoint, anti_windup_limit, back_calculation_gain)
        self.estimated_od = None
        self.q_in = None
        self.q_waste = None
        self.q_lagoon_set = 0.005    # hardcoded for testing
        self.q_lagoon = 0
        self.first_run = 0
        self._control_timer = QTimer(self)
        self._control_timer.timeout.connect(self.run_control_loop)

    @Slot(bool)
    def set_od_control_enabled(self, enabled: bool):
        """Enable or disable the OD control loop."""
        if enabled:
            self.run_control_loop()
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
    def calculate_dilution_flow(self, current_od: float, preferred_q_lagoon: float) -> tuple[float, float]:
        """Calculate the required inlet flow rate (q_in) based on the current OD measurement."""
        self.q_in, self.q_waste = self.od_control.calculate_dilution_flow(current_od, preferred_q_lagoon)
        return self.q_in, self.q_waste

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
        self.first_run = 0
        self.q_lagoon = 0

    def run_control_loop(self):
        """Update the current OD measurement and compute the new inlet flow rate."""
        if self.first_run == 0:
            q_in, q_waste = self.calculate_dilution_flow(self.od_control.A0, self.q_lagoon)
            self.estimated_od = self.estimate_od(self.od_control.A0)
        else:
            
            if self.first_run > 60:
                self.q_lagoon = self.q_lagoon_set

            if self.first_run > 240:
                self.od_control.set_A_setpoint(0.6)  # Change the setpoint after 2 minutes for testing

            q_in, q_waste = self.calculate_dilution_flow(self.estimated_od, self.q_lagoon)
            self.estimated_od = self.estimate_od(self.estimated_od)

        self.first_run += 1

        # self.q_waste, self.q_lagoon = self.calculate_outlet_flows(self.q_lagoon if self.q_lagoon is not None else 0.0)
        
        self.q_in_updated.emit(q_in)
        self.q_waste_updated.emit(self.q_waste)
        self.q_lagoon_updated.emit(self.q_lagoon)
        self.estimated_od_updated.emit(self.estimated_od)
        print(f"OD Control Loop: Setpoint={self.od_control.A_setpoint:.3f}, Estimated OD={self.estimated_od:.10f}, q_in={q_in:.10f}, q_waste={q_waste:.10f}, q_lagoon={self.q_lagoon:.6f}, error={self.od_control.error:.10f}, integral={self.od_control.integral:.10f}, mu_hat={self.od_control.mu_hat:.10f}, q_unsaturated={self.od_control.q_unsaturated:.10f}, actuator_mismatch={self.od_control.actuator_mismatch:.10f}")
