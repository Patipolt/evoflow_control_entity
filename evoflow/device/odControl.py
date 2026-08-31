"""
OD control class for EvoFlow control entity according to EvoFlow - OD control

Project: EvoFlow Innosuisse
Author: Patipol Thanuphol, Scientific Researcher at ZHAW — thau @zhaw.ch | patipol.thanu@gmail.com
Created: August 2026
"""

import math

class ODControl:
    """Class to control the optical density (OD) of a bioreactor using a PI controller."""

    @property
    def mu_hat(self):
        return self._mu_hat
    @mu_hat.setter
    def mu_hat(self, value):
        self._mu_hat = value
    @property
    def integral(self):
        return self._integral
    @integral.setter
    def integral(self, value):
        self._integral = value
    @property
    def error(self):
        return self._error
    @error.setter
    def error(self, value):
        self._error = value
    @property
    def q_unsaturated(self):
        return self._q_unsaturated
    @q_unsaturated.setter
    def q_unsaturated(self, value):
        self._q_unsaturated = value
    @property
    def actuator_mismatch(self):
        return self._actuator_mismatch
    @actuator_mismatch.setter
    def actuator_mismatch(self, value):
        self._actuator_mismatch = value
    @property
    def A_setpoint(self):
        return self._A_setpoint
    @A_setpoint.setter
    def A_setpoint(self, value):
        self._A_setpoint = value
    @property
    def A0(self):
        return self._A0
    @A0.setter
    def A0(self, value):
        if value <= 0:
            raise ValueError("A0 must be positive")
        self._A0 = value

    def __init__(self, V0: float, A0: float, mu0: float, kp: float, ki: float, q_max: float, q_lagoon_max: float, Ts: float, A_setpoint: float, anti_windup_limit: float, back_calculation_gain: float):
        if V0 <= 0 or q_max <= 0 or Ts <= 0:
            raise ValueError("All parameters must be positive")
        else:
            self.V0 = V0                        # (ml) Volume of the bioreactor
            self.q_max = q_max                  # (ml/s) Maximum flow rate of the pump
            self.q_lagoon_max = q_lagoon_max    # (ml/s) Maximum flow rate to the lagoon
            self.Ts = Ts                        # (s) Sampling time for the control loop

        if kp >= 0 or ki >= 0:
            raise ValueError("Both kp and ki must be negative for this control strategy")
        else:
            self.kp = kp                    # (ml/s) Proportional gain 
            self.ki = ki                    # (ml/s^2) Integral gain

        if A0 <= 0 or A_setpoint < 0:
            raise ValueError("Both A0 and A_setpoint must be non-negative")
        else:
            self.A0 = A0                    # Initial optical density
            self.A_setpoint = A_setpoint    # Desired optical density setpoint

        self.mu0 = mu0                                      # Initial bacterial growth rate
        self.mu_hat = 0                                     # Estimated bacterial growth rate
        self.integral = 0                                   # Integral term for PID control
        self.error = 0                                      # Error term for PID control
        self.q_unsaturated = 0                              # Unsaturated control action
        self.actuator_mismatch = 0                          # Mismatch between unsaturated and saturated control action
        self.anti_windup_limit = anti_windup_limit          # Limit for integral term to prevent windup
        self.back_calculation_gain = back_calculation_gain  # Back-calculation gain for anti-windup
        self.previous_od = None                             # Previous OD measurement
        self.previous_flow = None                           # Previous inlet flow rate

    def calculate_dilution_flow(self, current_od: float, preferred_q_lagoon: float) -> tuple[float, float]:
        """Update the control action based on the current OD measurement. Returns the computed inlet flow rate (q_in) to achieve the desired OD setpoint."""
        if self.previous_od is None and self.previous_flow is None:
            # For the first measurement, take the initial values as previous values
            self.previous_od = self.A0  # Assume initial OD is A0
            self.previous_flow = 0.0  # Assume no flow initially
            self.mu_hat = self.mu0  # Use initial growth rate for the first estimate
        else:
            # Estimate growth rate
            self.mu_hat = self.estimate_growth_rate(current_od)
        
        # Compute error
        self.error = self.A_setpoint - current_od

        # --- Back-calculation anti-windup ---
        # 1) Compute the unsaturated control action first
        self.q_unsaturated = self.V0 * (self.mu_hat + (self.kp * self.error) + (self.ki * self.integral))

        # 2) Saturate the flow to the physical actuator limits.
        q_lagoon = 0
        if preferred_q_lagoon > self.q_lagoon_max:
            q_lagoon = max(0, min(preferred_q_lagoon, self.q_lagoon_max))
        else:
            q_lagoon = preferred_q_lagoon

        q_in = max(q_lagoon, min(self.q_unsaturated, self.q_max))

        # 3) Back-calculate the actuator mismatch and pull the integral back toward the feasible range.
        #    This reduces the windup that would otherwise occur when the pump is pinned at 0 or q_max.
        self.actuator_mismatch = q_in - self.q_unsaturated
        self.integral += (self.error * self.Ts) + (self.back_calculation_gain * self.actuator_mismatch)
        self.integral = max(-self.anti_windup_limit, min(self.anti_windup_limit, self.integral))

        # --- Previous conditional anti-windup (just for my reference only) ---
        # is_min_saturated = q_unsaturated < 0 and error > 0
        # is_max_saturated = q_unsaturated > self.q_max and error < 0
        # if not (is_min_saturated or is_max_saturated):
        #     self.integral += self.error * self.Ts
        #     self.integral = max(-self.anti_windup_limit, min(self.anti_windup_limit, self.integral))
        
        # Update previous values for next iteration
        self.previous_od = current_od
        self.previous_flow = q_in

        # Calculate the waste flow rate based on the inlet flow and lagoon flow
        # ensure that the waste always pumps out more than the inlet as it is set by the height of the needle in the bioreactor.
        # Overpumping to the waste will not affect the OD control as the inlet flow is the only control variable for the OD.
        # This is not the actualy flow to the waste, but it is a safety measure to ensure that the waste is always pumped out more than the inlet.
        q_waste = q_in - q_lagoon
        q_waste = 1.1 * q_waste  # Overpump to waste by 10%
        
        return q_in, q_waste

    def estimate_growth_rate(self, current_od: float) -> float:
        r"""estimate_growth_rate(...)
        - Implements Equation 21:\[
        \hat{\mu}_k =
        \frac{q_{in,k-1}}{V}
        + \frac{1}{T_s}\ln\left(\frac{A_k}{A_{k-1}}\right)
        \]
        - Requires the current OD, previous OD, previous inlet flow, vessel volume, and elapsed sampling time.
        - The first measurement cannot produce an estimate.
        - Both OD values must be positive."""

        mu_hat = 0
        if self.previous_od is not None and self.previous_flow is not None and self.previous_od > 0 and current_od > 0:
            mu_hat = (self.previous_flow / self.V0) + (1 / self.Ts) * math.log(current_od / self.previous_od)

        return mu_hat

    def estimate_od(self, current_od: float) -> float:
        """Estimate the next OD based on the current OD, estimated growth rate, and inlet flow rate."""
        if self.previous_flow is None:
            raise ValueError("calculate_dilution_flow() must be called before estimate_od()")

        # Use the estimated growth rate to predict the next OD
        estimated_od = current_od * math.exp((self.mu_hat - (self.previous_flow / self.V0)) * self.Ts)
        return estimated_od

    def clear_control_state(self):
        """Reset the internal state of the controller."""
        self.mu_hat = 0
        self.integral = 0
        self.error = 0
        self.q_unsaturated = 0
        self.actuator_mismatch = 0
        self.previous_od = None
        self.previous_flow = None

    # def calculate_outlet_flows(self, preferred_q_lagoon: float) -> tuple[float, float]:
    #     """Calculate the outlet flow rate based on the inlet flow rate and the required flow-to-lagoon."""
    #     if self.previous_flow is None:
    #         raise ValueError("calculate_dilution_flow() must be called before calculate_outlet_flow()")

    #     # verify that q_lagoon is non-negative and less than or equal self.previous_flow
    #     if preferred_q_lagoon < 0:
    #         raise ValueError(f"preferred_q_lagoon must be non-negative, got {preferred_q_lagoon}")

    #     if preferred_q_lagoon > self.q_lagoon_max:
    #         q_lagoon = max(0, min(preferred_q_lagoon, self.q_lagoon_max))
    #         q_waste = self.previous_flow - q_lagoon
    #         return q_waste, q_lagoon
    #     else:
    #         q_waste = self.previous_flow - preferred_q_lagoon

    #         # ensure that the waste always pumps out more than the inlet as it is set by the height of the needle in the bioreactor.
    #         # Overpumping to the waste will not affect the OD control as the inlet flow is the only control variable for the OD.
    #         # This is not the actualy flow to the waste, but it is a safety measure to ensure that the waste is always pumped out more than the inlet.
    #         q_waste = 1.1 * q_waste  # Overpump to waste by 10%
    #         return q_waste, preferred_q_lagoon
