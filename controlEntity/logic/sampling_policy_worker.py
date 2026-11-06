"""
Sampling policy for the Sample Extraction device.

Project: EvoFlow Innosuisse
Author: Patipol Thanuphol, Scientific Researcher at ZHAW — thau @zhaw.ch | patipol.thanu@gmail.com
Created: October 2026
"""

import time
from PySide6.QtCore import QObject, QTimer, Signal, Slot, QCoreApplication, QEventLoop, QThread


class SamplingPolicy(QObject):
    """Class to handle the sample extraction sampling policy"""

    sample_extraction_requested = Signal(tuple)
    blink_timer_timeout = Signal()
    append_rack_filled_position_requested = Signal(tuple)
    delete_rack_filled_position_requested = Signal(bool)

    turn_pump_4_on_off = Signal(bool)

    sample_extraction_event = Signal(tuple, str)  # ((row, col), event_type)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.sample_extraction_auto_mode : bool = False
        self.auto_mode_start_position = (0, 0)  # Default start position for auto mode
        self.auto_mode_sampling_interval_ms = 600000  # Default sampling interval for auto mode (10 minutes)
        self._sample_extraction_customized_btn_blink_timer = None
        self._sample_extraction_sampling_interval_timer = None
        self._taking_sample_timer = None

        self.pump_4_flow_rate : float = 0.0  # Flow rate for pump 4, used to calculate the time needed for sample extraction
        self.volume_per_sample : float = 0.0  # Volume per sample, used to calculate the time needed for sample extraction

        # Flags
        self.sample_extraction_moving_done = False  # Track the moving status of the Sample Extraction device
        self.sample_extraction_taking_sample_done = False
        


    def start(self):
        """Start the sampling policy timers"""
        if self._sample_extraction_customized_btn_blink_timer is None:
            self._sample_extraction_customized_btn_blink_timer = QTimer(self)
            self._sample_extraction_customized_btn_blink_timer.timeout.connect(self._on_blink_timer_timeout)
        if self._sample_extraction_sampling_interval_timer is None:
            self._sample_extraction_sampling_interval_timer = QTimer(self)
            self._sample_extraction_sampling_interval_timer.setSingleShot(True)
            self._sample_extraction_sampling_interval_timer.timeout.connect(self._on_sampling_interval_timeout)
        if self._taking_sample_timer is None:
            self._taking_sample_timer = QTimer(self)
            self._taking_sample_timer.setSingleShot(True)
            self._taking_sample_timer.timeout.connect(self._on_taking_sample_timeout)

    @Slot()
    def stop(self):
        """Stop the sampling policy timers"""
        if self._sample_extraction_customized_btn_blink_timer is not None:
            self._sample_extraction_customized_btn_blink_timer.stop()
        if self._sample_extraction_sampling_interval_timer is not None:
            self._sample_extraction_sampling_interval_timer.stop()
        if self._taking_sample_timer is not None:
            self._taking_sample_timer.stop()
        self.sample_extraction_auto_mode = False

    @Slot(tuple)
    def start_manual_sample_extraction(self, position: tuple):
        """Start the sample extraction process"""
        try:
            self.sample_extraction_requested.emit((position[0], position[1]))
            self.append_rack_filled_position_requested.emit((position[0], position[1]))
            self.sample_extraction_event.emit((position[0], position[1]), "manual")
        except Exception as e:
            print(f"Failed to start sample extraction on Sample Extraction device: {e}")

    @Slot(bool)
    def start_auto_sample_extraction(self, start: bool):
        """Start timer-based sample extraction process"""
        if self._sample_extraction_customized_btn_blink_timer is not None and not self._sample_extraction_customized_btn_blink_timer.isActive() and self._sample_extraction_sampling_interval_timer is not None and not self._sample_extraction_sampling_interval_timer.isActive():
            self.sample_extraction_auto_mode = True
            self._sample_extraction_customized_btn_blink_timer.start(1000)
            self._sample_extraction_sampling_interval_timer.start(self.auto_mode_sampling_interval_ms)
        else:
            print("Auto sample extraction is already running or timers are not initialized.")

    @Slot(bool)
    def stop_auto_sample_extraction(self, stop: bool):
        """Stop timer-based sample extraction process"""
        self.sample_extraction_auto_mode = False
        if self._sample_extraction_customized_btn_blink_timer is not None:
            self._sample_extraction_customized_btn_blink_timer.stop()
        if self._sample_extraction_sampling_interval_timer is not None:
            self._sample_extraction_sampling_interval_timer.stop()
        if self._taking_sample_timer is not None:
            self._taking_sample_timer.stop()

    @Slot(bool)
    def handle_sample_extraction_auto_mode(self, mode: bool):
        """Handle the change in sample extraction mode (auto/manual)"""
        self.sample_extraction_auto_mode = mode
        if not self.sample_extraction_auto_mode:
            self.stop_auto_sample_extraction(True)

    @Slot(bool)
    def handle_sample_extraction_moving_status(self, moving: bool):
        """Handle the sample extraction moving status"""
        if moving:
            self.sample_extraction_moving_done = False
        else:
            self.sample_extraction_moving_done = True

    @Slot(bool)
    def turn_pump_4(self, condition: str):
        """Turn pump 4 on or off"""
        if condition == "on":
            self.turn_pump_4_on_off.emit(True)
        elif condition == "off":
            self.turn_pump_4_on_off.emit(False)
        # print(f"Pump 4 turned {condition} by SamplingPolicy.")

    @Slot(float)
    def handle_pump_4_flow_rate(self, pump4: float):
        """Handle the pump 4 flow rate and calculate the time needed for sample extraction"""
        # This will later be implemented differently, but for now, we will just use the pump4 flow rate to calculate the time needed for sample extraction.
        # Later, if the pump4 flow rate is controlled by Evoflow device, this value should come from the Evoflow device instead of the pump4 flow rate.
        self.pump_4_flow_rate = pump4

    @Slot(tuple)
    def set_auto_mode_start_position(self, position: tuple):
        """Set the start position for auto mode sample extraction"""
        self.auto_mode_start_position = position

    @Slot(int)
    def set_sampling_interval(self, interval_minutes: int):
        """Set the sampling interval for auto mode sample extraction"""
        # self.auto_mode_sampling_interval_ms = interval_minutes * 60000  # Convert minutes to milliseconds
        self.auto_mode_sampling_interval_ms = interval_minutes * 1000 # for development, set to seconds instead of minutes

    @Slot(int)
    def set_volume_per_sample(self, volume: int):
        """Set the volume per sample for calculating the time needed for sample extraction"""
        self.volume_per_sample = volume

    def _on_blink_timer_timeout(self):
        """Handle the blink timer timeout for the customized button"""
        if self._sample_extraction_customized_btn_blink_timer is not None and self._sample_extraction_customized_btn_blink_timer.isActive():
            self.blink_timer_timeout.emit()

    def _on_sampling_interval_timeout(self):
        """Handle the sampling interval timer timeout for auto mode sample extraction by increasing the position from starting point"""
        if self.sample_extraction_auto_mode:
            # turn off pump_4
            self.turn_pump_4("off")
            self._sleep(1000) # small delay to allow the pump to stop before moving the needle
            
            # bring the needle to the desired place
            if self.auto_mode_start_position is not None:
                row = self.auto_mode_start_position[0]
                col = self.auto_mode_start_position[1]
                if col <= 11:
                    if row <= 7:
                        # print(f"Starting auto sample extraction at position: Row {row}, Column {col}")
                        self.sample_extraction_requested.emit((row, col))
                        self.append_rack_filled_position_requested.emit((row, col))
                        self.sample_extraction_event.emit((row, col), "auto")
                        self.sample_extraction_moving_done = False
                        self._sleep(1000)    # small delay to allow the sample extraction device to start moving before waiting for the moving done flag
                        if not self._wait_for_flag('sample_extraction_moving_done', f'Sample Extraction moving to position ({row}, {col})', timeout_ms=18000000):   # just make it 5 hours for now
                            self.turn_pump_4("off")
                            return
                        row += 1
                        if row > 7:
                            row = 0
                            col += 1
                            if col > 11:
                                col = 0
                        self.auto_mode_start_position = (row, col)

            # turn on pump_4
            if not self.sample_extraction_auto_mode:
                return
            self.turn_pump_4("on")

            # wait for the sample extraction to finish, which is the _on_taking_sample_timeout() function linked to the current flow set on pump_4. It calculated the time needed to take the sample based on the flow rate and volume.
            # print(f"Starting taking sample timer for {self.volume_per_sample} ul at {self.pump_4_flow_rate} ul/min, which takes {int((self.volume_per_sample / self.pump_4_flow_rate) * 60)} seconds.")
            self.sample_extraction_taking_sample_done = False
            self._taking_sample_timer.start(int((self.volume_per_sample / self.pump_4_flow_rate) * 60 * 1000))  # Convert from ul/min to ms, assuming volume_per_sample is in ul and pump_4_flow_rate is in ul/min
            if not self._wait_for_flag('sample_extraction_taking_sample_done', 'Sample Extraction taking sample', timeout_ms=18000000):   # just make it 5 hours for now
                self.turn_pump_4("off")
                return

            # turn off pump_4
            self.turn_pump_4("off")
            self._sleep(1000) # small delay to allow the pump to stop before moving the needle

            # bring the needle back to waste position after taking sample
            if not self.sample_extraction_auto_mode:
                return
            # print("Returning the needle to waste position after taking sample.")
            self.sample_extraction_requested.emit((255, 255))
            self.sample_extraction_event.emit((255, 255), "auto")
            self.sample_extraction_moving_done = False
            self._sleep(1000)    # small delay to allow the sample extraction device to start moving before waiting for the moving done flag
            if not self._wait_for_flag('sample_extraction_moving_done', 'Sample Extraction moving to waste position', timeout_ms=18000000):   # just make it 5 hours for now
                self.turn_pump_4("off")
                return

            # turn on pump_4 to waste position
            if not self.sample_extraction_auto_mode:
                return
            self.turn_pump_4("on")

            # start the timer for the next sample extraction based on the sampling interval
            if self._sample_extraction_sampling_interval_timer is not None and self.sample_extraction_auto_mode:
                self._sample_extraction_sampling_interval_timer.start(self.auto_mode_sampling_interval_ms)

    def _on_taking_sample_timeout(self):
        """Handle the taking sample timer timeout"""
        self.sample_extraction_taking_sample_done = True

    def _sleep(self, ms: int):
        """Wait for ms milliseconds while still processing queued signals/timers in this thread."""
        loop = QEventLoop()
        QTimer.singleShot(ms, loop.quit)
        loop.exec()

    def _sleep(self, ms: int):
        """Wait for ms milliseconds while still processing queued signals/timers in this thread."""
        loop = QEventLoop()
        QTimer.singleShot(ms, loop.quit)
        loop.exec()

    def _wait_for_flag(self, flag_name: str, description: str, timeout_ms: int = 10000) -> bool:
        """Poll a boolean flag while letting the thread process queued signals."""
        start = time.monotonic()
        while not getattr(self, flag_name, False):
            # print(f"Waiting for {description}...")
            if not self.sample_extraction_auto_mode:
                return False
            # allow queued signals (e.g., ready updates) to be delivered in this thread
            QCoreApplication.processEvents(QEventLoop.AllEvents, 200)
            QThread.msleep(20)
            if timeout_ms and (time.monotonic() - start) * 1000 >= timeout_ms:
                print(f"Timeout waiting for {description}")
                return False
        if not self.sample_extraction_auto_mode:
            return False
        # reset the flag for the next use
        setattr(self, flag_name, False)
        return True
