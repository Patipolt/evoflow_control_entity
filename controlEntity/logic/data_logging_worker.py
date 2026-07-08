"""
Background worker for telemetry logging and history retrieval.

Stores telemetry in rotated SQLite files and serves timespan-bounded data for PlotWidget.
"""

from __future__ import annotations

import configparser
import copy
import csv
import datetime as dt
import os
import sqlite3
import time
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QTimer, Signal, Slot
from PySide6.QtWidgets import QMessageBox

from controlEntity.utils import resource_path
from evoflow.device.evoflow import EvoFlowTelemetry
from evoflow.device.sample_extraction import SampleExtractionTelemetry


class DataLoggingWorker(QObject):
    """Log telemetry snapshots at a configurable period and provide plot-ready history
    on demand. Uses rotated SQLite files for efficient storage and retrieval. This class logs all the telemetry data received
    from the evoflow worker and sample extraction worker, but only serves a subset of that data to the PlotWidget for visualization"""
    status_message = Signal(str)
    logging_state_changed = Signal(bool)
    plot_data_updated = Signal(dict, int)  # Emits plot payload dict for PlotWidget, along with all data points logged in the database
    message_box_requested = Signal(str, str, QMessageBox.Icon, bool)  # title, message, icon, response_needed
    x_axis_selection_mapped = Signal(object)  # Emits the mapped x-axis value in unix timestamp milliseconds that corresponds to the user's selection on the plot
    annotation_for_selected_x_axis = Signal(str)  # Emits the existing annotation text for the currently selected x-axis point, if it has an annotation, for display in the annotation editor
    update_configuration_requested = Signal()  # Signal to trigger re-reading of configuration file and applying new settings

    def __init__(self):
        super().__init__()
        config = self._read_settings_file()

        self._flow_rate_factor_1 = config.getfloat("flowRateConversionFactors", "pump_1", fallback=1.0)
        self._flow_rate_factor_2 = config.getfloat("flowRateConversionFactors", "pump_2", fallback=1.0)
        self._flow_rate_factor_3 = config.getfloat("flowRateConversionFactors", "pump_3", fallback=1.0)
        self._flow_rate_factor_4 = config.getfloat("flowRateConversionFactors", "pump_4", fallback=1.0)
        self._max_rows_per_db = config.getint("dataLogging", "max_rows_per_db", fallback=10000)

        self._latest_evoflow: dict[str, Any] = {}
        self._latest_sample_extraction: dict[str, Any] = {}

        self._is_logging = False
        self._sampling_time_seconds = 0
        self._timespan_minutes = max(1, config.getint("plotConfiguration", "timespan_minutes", fallback=10))
        self._history_offset_points = 0
        self._total_rows_logged = 0

        self._pending_timespan_minutes: int | None = None
        self._pending_history_offset_points: int | None = None
        self._plot_request_debounce_ms = 40
        self._plot_priority_guard_ms = 120

        self._session_dir: Path | None = None
        self._conn: sqlite3.Connection | None = None
        self._cursor: sqlite3.Cursor | None = None
        self._db_index = 0
        self._row_count_current_db = 0
        self._db_paths: list[Path] = []
        self._segment_start_ts_ms: int | None = None
        self._segment_end_ts_ms: int | None = None

        self._log_timer = QTimer(self)
        self._log_timer.timeout.connect(self._on_log_timer)

        self._plot_request_timer = QTimer(self)
        self._plot_request_timer.setSingleShot(True)
        self._plot_request_timer.timeout.connect(self._process_pending_plot_request)

        self._x_axis_mapped_selection: int | None = None  # Store the already mapped x-axis selection

        # For testing without actual telemetry from sample extraction device, initialize with dummy data.
        self._latest_sample_extraction = {
            "sample_row": int(0),
            "sample_col": int(0),
            "sample_done_flag": 1,
        }

    @Slot(EvoFlowTelemetry)
    def update_evoflow_telemetry(self, telemetry: EvoFlowTelemetry):
        """Cache the latest EvoFlow telemetry snapshot for periodic logging."""
        # This is EvoFlowTelemetry
        # self.pump_1_status  : bool = False
        # self.pump_1_sp      : float = 0.0
        # self.pump_1_speed   : float = 0.0
        # self.pump_2_status  : bool = False
        # self.pump_2_sp      : float = 0.0
        # self.pump_2_speed   : float = 0.0
        # self.pump_3_status  : bool = False
        # self.pump_3_sp      : float = 0.0
        # self.pump_3_speed   : float = 0.0
        # self.pump_4_status  : bool = False
        # self.pump_4_sp      : float = 0.0
        # self.pump_4_speed   : float = 0.0

        # self.magneticStirrer_bioreactor_status          : bool = False
        # self.magneticStirrer_bioreactor_sp              : float = 0.0
        # self.magneticStirrer_bioreactor_speed           : float = 0.0
        # self.magneticStirrer_bioreactor_fan_duty_cycle  : float = 0.0

        # self.magneticStirrer_lagoon_status          : bool = False
        # self.magneticStirrer_lagoon_sp              : float = 0.0
        # self.magneticStirrer_lagoon_speed           : float = 0.0
        # self.magneticStirrer_lagoon_fan_duty_cycle  : float  = 0.0

        # self.valve_bio2lag_status   : bool = False
        # self.valve_sug2lag_status   : bool = False

        # self.od_bioreactor_status   : bool = False
        # self.od_bioreactor_value    : float = 0.0
        # self.od_lagoon_status       : bool = False
        # self.od_lagoon_value        : float = 0.0

        # self.tempCtrl_bioreactor_status             : bool = False
        # self.tempCtrl_bioreactor_sp                 : float = 0.0
        # self.tempCtrl_bioreactor_value              : float = 0.0
        # self.tempCtrl_bioreactor_heater_duty_cycle  : float = 0.0

        # self.tempCtrl_lagoon_status             : bool = False
        # self.tempCtrl_lagoon_sp                 : float = 0.0
        # self.tempCtrl_lagoon_value              : float = 0.0
        # self.tempCtrl_lagoon_heater_duty_cycle  : float = 0.0

        # self.phtCount_lagoon_status     : bool = False
        # self.phtCount_lagoon_value      : float = 0.0
        # self.phtCount_lagoon_overlight  : bool = False

        # self.nucleo_temperature         : float = 0.0

        self._latest_evoflow = {
            "pump_1_status": 1 if bool(getattr(telemetry, "pump_1_status", False)) else 0,
            "pump_1_sp": float(getattr(telemetry, "pump_1_sp", 0.0)),
            "pump_1_speed": float(getattr(telemetry, "pump_1_speed", 0.0)),
            "pump_2_status": 1 if bool(getattr(telemetry, "pump_2_status", False)) else 0,
            "pump_2_sp": float(getattr(telemetry, "pump_2_sp", 0.0)),
            "pump_2_speed": float(getattr(telemetry, "pump_2_speed", 0.0)),
            "pump_3_status": 1 if bool(getattr(telemetry, "pump_3_status", False)) else 0,
            "pump_3_sp": float(getattr(telemetry, "pump_3_sp", 0.0)),
            "pump_3_speed": float(getattr(telemetry, "pump_3_speed", 0.0)),
            "pump_4_status": 1 if bool(getattr(telemetry, "pump_4_status", False)) else 0,
            "pump_4_sp": float(getattr(telemetry, "pump_4_sp", 0.0)),
            "pump_4_speed": float(getattr(telemetry, "pump_4_speed", 0.0)),
            "magneticStirrer_bioreactor_status": 1 if bool(getattr(telemetry, "magneticStirrer_bioreactor_status", False)) else 0,
            "magneticStirrer_bioreactor_sp": float(getattr(telemetry, "magneticStirrer_bioreactor_sp", 0.0)),
            "magneticStirrer_bioreactor_speed": float(getattr(telemetry, "magneticStirrer_bioreactor_speed", 0.0)),
            "magneticStirrer_bioreactor_fan_duty_cycle": float(getattr(telemetry, "magneticStirrer_bioreactor_fan_duty_cycle", 0.0)),
            "magneticStirrer_lagoon_status": 1 if bool(getattr(telemetry, "magneticStirrer_lagoon_status", False)) else 0,
            "magneticStirrer_lagoon_sp": float(getattr(telemetry, "magneticStirrer_lagoon_sp", 0.0)),
            "magneticStirrer_lagoon_speed": float(getattr(telemetry, "magneticStirrer_lagoon_speed", 0.0)),
            "magneticStirrer_lagoon_fan_duty_cycle": float(getattr(telemetry, "magneticStirrer_lagoon_fan_duty_cycle", 0.0)),
            "valve_bio2lag_status": 1 if bool(getattr(telemetry, "valve_bio2lag_status", False)) else 0,
            "valve_sug2lag_status": 1 if bool(getattr(telemetry, "valve_sug2lag_status", False)) else 0,
            "od_bioreactor_status": 1 if bool(getattr(telemetry, "od_bioreactor_status", False)) else 0,
            "od_bioreactor_value": float(getattr(telemetry, "od_bioreactor_value", 0.0)),
            "od_lagoon_status": 1 if bool(getattr(telemetry, "od_lagoon_status", False)) else 0,
            "od_lagoon_value": float(getattr(telemetry, "od_lagoon_value", 0.0)),
            "tempCtrl_bioreactor_status": 1 if bool(getattr(telemetry, "tempCtrl_bioreactor_status", False)) else 0,
            "tempCtrl_bioreactor_sp": float(getattr(telemetry, "tempCtrl_bioreactor_sp", 0.0)),
            "tempCtrl_bioreactor_value": float(getattr(telemetry, "tempCtrl_bioreactor_value", 0.0)),
            "tempCtrl_bioreactor_heater_duty_cycle": float(getattr(telemetry, "tempCtrl_bioreactor_heater_duty_cycle", 0.0)),
            "tempCtrl_lagoon_status": 1 if bool(getattr(telemetry, "tempCtrl_lagoon_status", False)) else 0,
            "tempCtrl_lagoon_sp": float(getattr(telemetry, "tempCtrl_lagoon_sp", 0.0)),
            "tempCtrl_lagoon_value": float(getattr(telemetry, "tempCtrl_lagoon_value", 0.0)),
            "tempCtrl_lagoon_heater_duty_cycle": float(getattr(telemetry, "tempCtrl_lagoon_heater_duty_cycle", 0.0)),
            "phtCount_lagoon_status": 1 if bool(getattr(telemetry, "phtCount_lagoon_status", False)) else 0,
            "phtCount_lagoon_value": float(getattr(telemetry, "phtCount_lagoon_value", 0.0)),
            "phtCount_lagoon_overlight": 1 if bool(getattr(telemetry, "phtCount_lagoon_overlight", False)) else 0,
            "nucleo_temperature": float(getattr(telemetry, "nucleo_temperature", 0.0)),
        }

    @Slot(SampleExtractionTelemetry)
    def update_sample_extraction_telemetry(self, telemetry: SampleExtractionTelemetry):
        """Cache the latest sample extraction telemetry snapshot for periodic logging."""
        # This is SampleExtractionTelemetry
        # self.position = [0, 0]  # Row, Col
        # self.done_flag = False
        self._latest_sample_extraction = {
            "sample_row": int(getattr(telemetry, "position", [252, 252])[0]),
            "sample_col": int(getattr(telemetry, "position", [252, 252])[1]),
            "sample_done_flag": 1 if bool(getattr(telemetry, "done_flag", False)) else 0,
        }

    @Slot(str, str, int)
    def start_logging(self, log_name: str, log_directory: str, sampling_time_seconds: int):
        """Start periodic telemetry logging to rotated SQLite files"""
        try:
            safe_name = self._sanitize_log_name(log_name)
            base_dir = Path(log_directory).expanduser() if log_directory else Path.cwd() / "logs"
            base_dir.mkdir(parents=True, exist_ok=True)

            ts_label = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
            self._session_dir = base_dir / f"{safe_name}_{ts_label}"
            self._session_dir.mkdir(parents=True, exist_ok=True)

            self._sampling_time_seconds = max(1, int(sampling_time_seconds))
            self._history_offset_points = 0
            self._total_rows_logged = 0

            self._db_index = 0
            self._row_count_current_db = 0
            self._db_paths = []
            self._segment_start_ts_ms = None
            self._segment_end_ts_ms = None

            self._open_new_segment_db()

            self._is_logging = True
            self._log_timer.start(self._sampling_time_seconds * 1000)
            self._on_log_timer()  # Write first sample immediately if telemetry exists.

            self.logging_state_changed.emit(True)
            self.status_message.emit(f"Data logging started: {self._session_dir}")
        except Exception as exc:
            self.status_message.emit(f"Failed to start logging: {exc}")

    @Slot()
    def stop_logging(self):
        """Stop logging and close active database"""
        if not self._is_logging:
            self.status_message.emit("Data logging is not running.")
            return

        self._log_timer.stop()
        self._is_logging = False
        self._close_current_segment_db()
        self.logging_state_changed.emit(False)
        self.status_message.emit("Data logging stopped.")

    @Slot(int, int)
    def request_plot_view(self, timespan_minutes: int, history_offset_points: int):
        """Load a plot view from a timespan window anchored at an offset from newest"""
        self._queue_plot_request(timespan_minutes, history_offset_points)

    @Slot(str)
    def load_logged_data_from_directory(self, directory_path: str):
        """Load telemetry DB files from a selected folder and display newest window"""
        if self._is_logging:
            self.status_message.emit("Stop active logging before opening logged data from another folder.")
            self.message_box_requested.emit("Stop Logging", "Stop active logging before opening logged data from another folder.", QMessageBox.Icon.Warning, False)
            return

        selected_dir = Path(directory_path).expanduser()
        if not selected_dir.exists() or not selected_dir.is_dir():
            self.status_message.emit(f"Invalid logged-data folder: {selected_dir}")
            self.message_box_requested.emit("Invalid Folder", f"The selected folder does not exist or is not a directory:\n{selected_dir}", QMessageBox.Icon.Warning, False) 
            return

        discovered = self._discover_db_files(selected_dir)
        if not discovered:
            self.status_message.emit("No telemetry SQL files found in selected folder.")
            self.message_box_requested.emit("No Data Found", f"No telemetry SQL files found in selected folder:\n{selected_dir}", QMessageBox.Icon.Warning, False)
            return

        self._session_dir = selected_dir
        self._db_paths = discovered
        self._history_offset_points = 0

        self._total_rows_logged = self._count_total_logged_rows()
        self._queue_plot_request(self._timespan_minutes, 0, debounce_ms=0)
        self.status_message.emit(
            f"Loaded logged data from {selected_dir} ({len(discovered)} files, {self._total_rows_logged} points)."
        )

    @Slot()
    def export_logged_data_to_csv(self):
        """Export all logged telemetry data in current session folder to a single CSV file."""
        if not self._session_dir or not self._session_dir.exists():
            self.status_message.emit("No active session or logged data to export.")
            self.message_box_requested.emit("No Data", "No active session or logged data to export.", QMessageBox.Icon.Warning, False)
            return

        csv_path = self._session_dir / f"{self._session_dir.name}_export.csv"
        
        if self._is_logging:
            self.status_message.emit("Stop active logging before exporting to CSV.")
            self.message_box_requested.emit("Stop Logging", "Stop active logging before exporting to CSV.", QMessageBox.Icon.Warning, False)
            return
    
        try:
            with open(csv_path, "w", newline="") as csvfile:
                columns = self._get_db_columns()
                if not columns:
                    self.status_message.emit("No telemetry columns available to export.")
                    self.message_box_requested.emit("Export Failed", "No telemetry columns available to export.", QMessageBox.Icon.Warning, False)
                    return

                writer = csv.writer(csvfile)
                writer.writerow(columns + ["ts_local"])

                ts_unix_ms_idx = columns.index("ts_unix_ms") if "ts_unix_ms" in columns else None

                # Write rows from all DB files in order
                for db_path in sorted(self._db_paths):
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    cursor.execute("SELECT * FROM telemetry")
                    for row in cursor.fetchall():
                        ts_local = ""
                        if ts_unix_ms_idx is not None:
                            try:
                                ts_ms = int(row[ts_unix_ms_idx])
                                ts_local = dt.datetime.fromtimestamp(
                                    ts_ms / 1000.0,
                                    tz=dt.timezone.utc,
                                ).astimezone().isoformat()
                            except Exception:
                                ts_local = ""

                        writer.writerow(list(row) + [ts_local])
                    conn.close()
            self.message_box_requested.emit("Export Successful", f"Export successful: {csv_path}", QMessageBox.Icon.Information, False)
        except Exception as exc:
            self.message_box_requested.emit("Export Failed", f"Export failed: {exc}", QMessageBox.Icon.Warning, False)

    def _get_db_columns(self) -> list[str]:
        """Return the list of column names in the telemetry table, based on the first DB file."""
        if not self._db_paths:
            return []

        try:
            conn = sqlite3.connect(self._db_paths[0])
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(telemetry)")
            columns_info = cursor.fetchall()
            conn.close()
            return [col[1] for col in columns_info]  # Extract column names
        except Exception as exc:
            self.status_message.emit(f"Failed to retrieve DB columns: {exc}")
            return []

    @Slot()
    def shutdown(self):
        """Release resources on application shutdown"""
        if self._is_logging:
            self.stop_logging()
        else:
            self._close_current_segment_db()

    def _on_log_timer(self):
        """Periodic writer callback"""
        if not self._is_logging:
            return

        if not self._latest_evoflow or not self._latest_sample_extraction:
            return

        now = dt.datetime.now(dt.timezone.utc)
        ts_ms = int(now.timestamp() * 1000)
        iso_utc = now.isoformat()

        evoflow_snapshot = copy.deepcopy(self._latest_evoflow)
        sample_snapshot = copy.deepcopy(self._latest_sample_extraction)

        flow_rate_1 = float(evoflow_snapshot.get("pump_1_speed", 0.0)) * self._flow_rate_factor_1
        flow_rate_2 = float(evoflow_snapshot.get("pump_2_speed", 0.0)) * self._flow_rate_factor_2
        flow_rate_3 = float(evoflow_snapshot.get("pump_3_speed", 0.0)) * self._flow_rate_factor_3
        flow_rate_4 = float(evoflow_snapshot.get("pump_4_speed", 0.0)) * self._flow_rate_factor_4

        # Keep derived flow rates in the full telemetry snapshot for later analysis.
        evoflow_snapshot["flow_rate_pump1"] = float(flow_rate_1)
        evoflow_snapshot["flow_rate_pump2"] = float(flow_rate_2)
        evoflow_snapshot["flow_rate_pump3"] = float(flow_rate_3)
        evoflow_snapshot["flow_rate_pump4"] = float(flow_rate_4)

        row = (
            ts_ms,
            iso_utc,
            int(evoflow_snapshot.get("pump_1_status", 0)),
            format(float(evoflow_snapshot.get("pump_1_sp", 0.0)), ".2f"),
            format(float(evoflow_snapshot.get("pump_1_speed", 0.0)), ".2f"),
            int(evoflow_snapshot.get("pump_2_status", 0)),
            format(float(evoflow_snapshot.get("pump_2_sp", 0.0)), ".2f"),
            format(float(evoflow_snapshot.get("pump_2_speed", 0.0)), ".2f"),
            int(evoflow_snapshot.get("pump_3_status", 0)),
            format(float(evoflow_snapshot.get("pump_3_sp", 0.0)), ".2f"),
            format(float(evoflow_snapshot.get("pump_3_speed", 0.0)), ".2f"),
            int(evoflow_snapshot.get("pump_4_status", 0)),
            format(float(evoflow_snapshot.get("pump_4_sp", 0.0)), ".2f"),
            format(float(evoflow_snapshot.get("pump_4_speed", 0.0)), ".2f"),
            int(evoflow_snapshot.get("magneticStirrer_bioreactor_status", 0)),
            format(float(evoflow_snapshot.get("magneticStirrer_bioreactor_sp", 0.0)), ".2f"),
            format(float(evoflow_snapshot.get("magneticStirrer_bioreactor_speed", 0.0)), ".2f"),
            format(float(evoflow_snapshot.get("magneticStirrer_bioreactor_fan_duty_cycle", 0.0)), ".2f"),
            int(evoflow_snapshot.get("magneticStirrer_lagoon_status", 0)),
            format(float(evoflow_snapshot.get("magneticStirrer_lagoon_sp", 0.0)), ".2f"),
            format(float(evoflow_snapshot.get("magneticStirrer_lagoon_speed", 0.0)), ".2f"),
            format(float(evoflow_snapshot.get("magneticStirrer_lagoon_fan_duty_cycle", 0.0)), ".2f"),
            int(evoflow_snapshot.get("valve_bio2lag_status", 0)),
            int(evoflow_snapshot.get("valve_sug2lag_status", 0)),
            int(evoflow_snapshot.get("od_bioreactor_status", 0)),
            format(float(evoflow_snapshot.get("od_bioreactor_value", 0.0)), ".2f"),
            int(evoflow_snapshot.get("od_lagoon_status", 0)),
            format(float(evoflow_snapshot.get("od_lagoon_value", 0.0)), ".2f"),
            int(evoflow_snapshot.get("tempCtrl_bioreactor_status", 0)),
            format(float(evoflow_snapshot.get("tempCtrl_bioreactor_sp", 0.0)), ".2f"),
            format(float(evoflow_snapshot.get("tempCtrl_bioreactor_value", 0.0)), ".2f"),
            format(float(evoflow_snapshot.get("tempCtrl_bioreactor_heater_duty_cycle", 0.0)), ".2f"),
            int(evoflow_snapshot.get("tempCtrl_lagoon_status", 0)),
            format(float(evoflow_snapshot.get("tempCtrl_lagoon_sp", 0.0)), ".2f"),
            format(float(evoflow_snapshot.get("tempCtrl_lagoon_value", 0.0)), ".2f"),
            format(float(evoflow_snapshot.get("tempCtrl_lagoon_heater_duty_cycle", 0.0)), ".2f"),
            int(evoflow_snapshot.get("phtCount_lagoon_status", 0)),
            format(float(evoflow_snapshot.get("phtCount_lagoon_value", 0.0)), ".2f"),
            int(evoflow_snapshot.get("phtCount_lagoon_overlight", 0)),
            format(float(evoflow_snapshot.get("nucleo_temperature", 0.0)), ".2f"),
            format(float(flow_rate_1), ".3f"),
            format(float(flow_rate_2), ".3f"),
            format(float(flow_rate_3), ".3f"),
            format(float(flow_rate_4), ".3f"),
            int(sample_snapshot.get("sample_row", 0)),
            int(sample_snapshot.get("sample_col", 0)),
            int(sample_snapshot.get("sample_done_flag", 0)),
        )

        if not self._cursor or not self._conn:
            return

        self._cursor.execute(
            """
            INSERT INTO telemetry (
                ts_unix_ms,
                ts_utc,
                pump_1_status,
                pump_1_sp,
                pump_1_speed,
                pump_2_status,
                pump_2_sp,
                pump_2_speed,
                pump_3_status,
                pump_3_sp,
                pump_3_speed,
                pump_4_status,
                pump_4_sp,
                pump_4_speed,
                magneticStirrer_bioreactor_status,
                magneticStirrer_bioreactor_sp,
                magneticStirrer_bioreactor_speed,
                magneticStirrer_bioreactor_fan_duty_cycle,
                magneticStirrer_lagoon_status,
                magneticStirrer_lagoon_sp,
                magneticStirrer_lagoon_speed,
                magneticStirrer_lagoon_fan_duty_cycle,
                valve_bio2lag_status,
                valve_sug2lag_status,
                od_bioreactor_status,
                od_bioreactor_value,
                od_lagoon_status,
                od_lagoon_value,
                tempCtrl_bioreactor_status,
                tempCtrl_bioreactor_sp,
                tempCtrl_bioreactor_value,
                tempCtrl_bioreactor_heater_duty_cycle,
                tempCtrl_lagoon_status,
                tempCtrl_lagoon_sp,
                tempCtrl_lagoon_value,
                tempCtrl_lagoon_heater_duty_cycle,
                phtCount_lagoon_status,
                phtCount_lagoon_value,
                phtCount_lagoon_overlight,
                nucleo_temperature,
                flow_rate_pump1,
                flow_rate_pump2,
                flow_rate_pump3,
                flow_rate_pump4,
                sample_row,
                sample_col,
                sample_done_flag,
                Annotations
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 
                ?, ?, ?, ?, ?, ?, ?, ''
            )
            """,
            row,
        )
        self._conn.commit()

        self._row_count_current_db += 1
        self._total_rows_logged += 1
        if self._segment_start_ts_ms is None:
            self._segment_start_ts_ms = ts_ms
        self._segment_end_ts_ms = ts_ms

        if self._row_count_current_db >= self._max_rows_per_db:
            self._rotate_segment_db()

        # Queue a plot refresh outside the timer callback so logging stays responsive.
        self._queue_plot_request(self._timespan_minutes, self._history_offset_points, debounce_ms=0)

    def _queue_plot_request(self, timespan_minutes: int, history_offset_points: int, debounce_ms: int | None = None):
        """Coalesce plot updates and process them when logging timer is not near deadline."""
        self._pending_timespan_minutes = max(1, int(timespan_minutes))
        self._pending_history_offset_points = max(0, int(history_offset_points))

        delay_ms = self._plot_request_debounce_ms if debounce_ms is None else max(0, int(debounce_ms))
        if self._plot_request_timer.isActive():
            self._plot_request_timer.stop()
        self._plot_request_timer.start(delay_ms)

    def _process_pending_plot_request(self):
        """Serve latest queued plot request while keeping sampling callback priority."""
        if self._pending_timespan_minutes is None or self._pending_history_offset_points is None:
            return

        if self._is_logging and self._log_timer.isActive():
            remaining_ms = self._log_timer.remainingTime()
            if 0 <= remaining_ms <= self._plot_priority_guard_ms:
                self._plot_request_timer.start(remaining_ms + 5)
                return

        self._timespan_minutes = int(self._pending_timespan_minutes)
        self._history_offset_points = int(self._pending_history_offset_points)

        self._pending_timespan_minutes = None
        self._pending_history_offset_points = None

        self.plot_data_updated.emit(
            self._load_plot_data(self._timespan_minutes, self._history_offset_points),
            self._total_rows_logged,
        )
    
    def _count_total_logged_rows(self) -> int:
        """Count total rows across all segment DB files for status reporting"""
        total_rows = 0
        for db_path in self._db_paths:
            conn = sqlite3.connect(db_path)
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM telemetry")
                count = cursor.fetchone()[0]
                total_rows += count
            finally:
                conn.close()
        return total_rows

    def _rotate_segment_db(self):
        """Close current DB segment and open a new one"""
        self._close_current_segment_db()
        self._open_new_segment_db()

    def _open_new_segment_db(self):
        """Create/open next segment SQLite file and ensure schema"""
        if self._session_dir is None:
            raise RuntimeError("Session directory is not set.")

        self._db_index += 1
        db_path = self._session_dir / f"telemetry_{self._db_index:04d}.sqlite"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute(
            # id INTEGER PRIMARY KEY AUTOINCREMENT, Put this in if id is needed
            """
            CREATE TABLE IF NOT EXISTS telemetry (
                ts_unix_ms INTEGER NOT NULL,
                ts_utc TEXT NOT NULL,
                pump_1_status INTEGER,
                pump_1_sp REAL,
                pump_1_speed REAL,
                pump_2_status INTEGER,
                pump_2_sp REAL,
                pump_2_speed REAL,
                pump_3_status INTEGER,
                pump_3_sp REAL,
                pump_3_speed REAL,
                pump_4_status INTEGER,
                pump_4_sp REAL,
                pump_4_speed REAL,
                magneticStirrer_bioreactor_status INTEGER,
                magneticStirrer_bioreactor_sp REAL,
                magneticStirrer_bioreactor_speed REAL,
                magneticStirrer_bioreactor_fan_duty_cycle REAL,
                magneticStirrer_lagoon_status INTEGER,
                magneticStirrer_lagoon_sp REAL,
                magneticStirrer_lagoon_speed REAL,
                magneticStirrer_lagoon_fan_duty_cycle REAL,
                valve_bio2lag_status INTEGER,
                valve_sug2lag_status INTEGER,
                od_bioreactor_status INTEGER,
                od_bioreactor_value REAL,
                od_lagoon_status INTEGER,
                od_lagoon_value REAL,
                tempCtrl_bioreactor_status INTEGER,
                tempCtrl_bioreactor_sp REAL,
                tempCtrl_bioreactor_value REAL,
                tempCtrl_bioreactor_heater_duty_cycle REAL,
                tempCtrl_lagoon_status INTEGER,
                tempCtrl_lagoon_sp REAL,
                tempCtrl_lagoon_value REAL,
                tempCtrl_lagoon_heater_duty_cycle REAL,
                phtCount_lagoon_status INTEGER,
                phtCount_lagoon_value REAL,
                phtCount_lagoon_overlight INTEGER,
                nucleo_temperature REAL,
                flow_rate_pump1 REAL,
                flow_rate_pump2 REAL,
                flow_rate_pump3 REAL,
                flow_rate_pump4 REAL,
                sample_row INTEGER,
                sample_col INTEGER,
                sample_done_flag INTEGER,
                Annotations TEXT
            )
            """
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_ts ON telemetry(ts_unix_ms)")
        cursor.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
        conn.commit()

        self._conn = conn
        self._cursor = cursor
        self._row_count_current_db = 0
        self._segment_start_ts_ms = None
        self._segment_end_ts_ms = None
        self._db_paths.append(db_path)

    def _close_current_segment_db(self):
        """Finalize metadata and close active DB connection"""
        if not self._conn or not self._cursor:
            return

        try:
            if self._segment_start_ts_ms is not None:
                self._cursor.execute(
                    "INSERT OR REPLACE INTO meta(key, value) VALUES(?, ?)",
                    ("start_ts_unix_ms", str(self._segment_start_ts_ms)),
                )
            if self._segment_end_ts_ms is not None:
                self._cursor.execute(
                    "INSERT OR REPLACE INTO meta(key, value) VALUES(?, ?)",
                    ("end_ts_unix_ms", str(self._segment_end_ts_ms)),
                )
            self._cursor.execute(
                "INSERT OR REPLACE INTO meta(key, value) VALUES(?, ?)",
                ("row_count", str(self._row_count_current_db)),
            )
            self._conn.commit()
        finally:
            self._conn.close()
            self._conn = None
            self._cursor = None

    def _load_plot_data(self, timespan_minutes: int, history_offset_points: int = 0) -> dict[str, list[float]]:
        """Read telemetry from rotated DB files and return plot-series arrays"""
        payload = {
            "x_seconds": [],
            "flow_rate_pump1": [],
            "flow_rate_pump2": [],
            "pht_count_lagoon": [],
            "temp_bioreactor": [],
            "temp_lagoon": [],
            "temp_bioreactor_sp": [],
            "temp_lagoon_sp": [],
            "od_bioreactor": [],
            "od_lagoon": [],
            "sample_event": [],
            "annotation_event": [],
        }

        if self._session_dir is None:
            return payload

        db_files = list(self._db_paths) if self._db_paths else sorted(self._session_dir.glob("telemetry_*.sqlite"))
        if not db_files:
            return payload

        anchor_ts_ms = self._resolve_anchor_timestamp_ms(db_files, history_offset_points)
        if anchor_ts_ms is None:
            return payload

        cutoff_ms = anchor_ts_ms - (max(1, timespan_minutes) * 60 * 1000)
        rows: list[tuple[Any, ...]] = []

        for db_path in db_files:
            conn = sqlite3.connect(db_path)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT
                        ts_unix_ms,
                        od_bioreactor_value,
                        od_lagoon_value,
                        phtCount_lagoon_value,
                        tempCtrl_bioreactor_value,
                        tempCtrl_lagoon_value,
                        tempCtrl_bioreactor_sp,
                        tempCtrl_lagoon_sp,
                        flow_rate_pump1,
                        flow_rate_pump2,
                        sample_done_flag,
                        Annotations
                    FROM telemetry
                    WHERE ts_unix_ms >= ? AND ts_unix_ms <= ?
                    ORDER BY ts_unix_ms ASC
                    """,
                    (cutoff_ms, anchor_ts_ms),
                )
                rows.extend(cursor.fetchall())
            finally:
                conn.close()

        if not rows:
            return payload

        rows.sort(key=lambda item: item[0])

        for item in rows:
            ts_ms = int(item[0])
            payload["x_seconds"].append(ts_ms / 1000.0)
            payload["od_bioreactor"].append(float(item[1]))
            payload["od_lagoon"].append(float(item[2]))
            payload["pht_count_lagoon"].append(float(item[3]))
            payload["temp_bioreactor"].append(float(item[4]))
            payload["temp_lagoon"].append(float(item[5]))
            payload["temp_bioreactor_sp"].append(float(item[6]))
            payload["temp_lagoon_sp"].append(float(item[7]))
            payload["flow_rate_pump1"].append(float(item[8]))
            payload["flow_rate_pump2"].append(float(item[9]))
            payload["sample_event"].append(float(item[10]))
            payload["annotation_event"].append(str(item[11]) if item[11] is not None else "")

        return payload

    def _resolve_anchor_timestamp_ms(self, db_files: list[Path], history_offset_points: int) -> int | None:
        """Return right-edge timestamp for view window based on offset from newest row"""
        total_rows = self._count_total_logged_rows()
        if total_rows <= 0:
            return None

        remaining = min(max(0, int(history_offset_points)), total_rows - 1)

        for db_path in reversed(db_files):
            conn = sqlite3.connect(db_path)
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM telemetry")
                db_count = int(cursor.fetchone()[0])
                if db_count <= 0:
                    continue

                if remaining < db_count:
                    cursor.execute(
                        """
                        SELECT ts_unix_ms
                        FROM telemetry
                        ORDER BY ts_unix_ms DESC
                        LIMIT 1 OFFSET ?
                        """,
                        (remaining,),
                    )
                    row = cursor.fetchone()
                    return int(row[0]) if row else None

                remaining -= db_count
            finally:
                conn.close()

        return None

    def _discover_db_files(self, session_dir: Path) -> list[Path]:
        """Discover telemetry DB files from a session folder"""
        candidates = sorted(session_dir.glob("telemetry_*.sqlite"))
        if not candidates:
            candidates = sorted(session_dir.glob("*.sqlite")) + sorted(session_dir.glob("*.db"))

        valid_paths: list[Path] = []
        for db_path in candidates:
            if self._is_valid_telemetry_db(db_path):
                valid_paths.append(db_path)

        return valid_paths
    
    @Slot(object)
    def map_selected_x_axis_to_closest_data_point(self, selected_x_ms: object):
        """Map selected x-axis value in seconds to closest timestamp the first one in the past in telemetry and emit for annotation"""
        if not self._session_dir or not self._db_paths:
            return

        # instead of searching for the closest timestamp across all DB files, we will find the first timestamp in the past relative to the selected_x_ms, 
        # starting from the newest DB file and moving backwards. This way, we ensure that the annotation corresponds to a real data point that is at or before the selected x-axis value.
        # and probably reduce searching time for large datasets, since we expect users to select recent points more often than very old points.
        target_ts_ms = int(selected_x_ms)
        for db_path in reversed(self._db_paths):
            conn = sqlite3.connect(db_path)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT ts_unix_ms
                    FROM telemetry
                    WHERE ts_unix_ms <= ?
                    ORDER BY ts_unix_ms DESC
                    LIMIT 1
                    """,
                    (target_ts_ms,),
                )
                row = cursor.fetchone()
                if row:
                    closest_ts_ms = int(row[0])
                    self.x_axis_selection_mapped.emit(closest_ts_ms)
                    self._x_axis_mapped_selection = closest_ts_ms
                    break
            finally:
                conn.close()

        found_row = False
        has_annotation = False
        existing_note = ""
        # Also find if there is an annotation at the selected timestamp and emit it for display in the annotation editor
        for db_path in reversed(self._db_paths):
            conn = sqlite3.connect(db_path)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT Annotations
                    FROM telemetry
                    WHERE ts_unix_ms = ?
                    LIMIT 1
                    """,
                    (self._x_axis_mapped_selection,),
                )
                row = cursor.fetchone()
                if not row:
                    continue

                found_row = True
                existing_note = "" if row[0] is None else str(row[0]).strip()
                has_annotation = existing_note != ""

                if has_annotation:
                    self.annotation_for_selected_x_axis.emit(existing_note)
                    break
                else:
                    self.annotation_for_selected_x_axis.emit("")
                    break
            finally:
                conn.close()

    @Slot(str)
    def add_annotation_to_selected_x_axis(self, annotation_text: str):
        """Add an annotation to the currently mapped x-axis timestamp"""
        if self._x_axis_mapped_selection is None:
            self.status_message.emit("No x-axis point selected for annotation.")
            return

        ts_ms = self._x_axis_mapped_selection
        note = annotation_text.strip()
        updated = False

        for db_path in reversed(self._db_paths):
            conn = sqlite3.connect(db_path)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE telemetry
                    SET Annotations = ?
                    WHERE ts_unix_ms = ?
                    """,
                    (note, ts_ms),
                )
                conn.commit()
                if cursor.rowcount > 0:
                    updated = True
                    break
            finally:
                conn.close()

        converted_ts = self.convert_timestamp_ms_to_local_iso(ts_ms)

        if updated:
            self.status_message.emit(f"Annotation added to timestamp {converted_ts}.")
            self.message_box_requested.emit("Annotation Added", f"Annotation added to timestamp {converted_ts}:\n{note}", QMessageBox.Icon.Information, False)
            self.update_configuration_requested.emit()  # Trigger plot refresh to show annotation markers
        else:
            self.status_message.emit(f"No telemetry row found for timestamp {converted_ts}.")
            self.message_box_requested.emit("Annotation Failed", f"No telemetry row found for timestamp {converted_ts}. Annotation not added.", QMessageBox.Icon.Warning, False)
    
    @Slot()
    def delete_annotation_at_selected_x_axis(self):
        """Delete annotation at the currently mapped x-axis timestamp"""
        if self._x_axis_mapped_selection is None:
            self.status_message.emit("No x-axis point selected for annotation deletion.")
            return

        ts_ms = self._x_axis_mapped_selection
        found_row = False
        has_annotation = False
        deleted = False

        for db_path in reversed(self._db_paths):
            conn = sqlite3.connect(db_path)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT Annotations
                    FROM telemetry
                    WHERE ts_unix_ms = ?
                    LIMIT 1
                    """,
                    (ts_ms,),
                )
                row = cursor.fetchone()
                if not row:
                    continue

                found_row = True
                existing_note = "" if row[0] is None else str(row[0]).strip()
                has_annotation = existing_note != ""

                if not has_annotation:
                    break

                cursor.execute(
                    """
                    UPDATE telemetry
                    SET Annotations = ''
                    WHERE ts_unix_ms = ?
                    """,
                    (ts_ms,),
                )
                conn.commit()
                deleted = cursor.rowcount > 0
                break
            finally:
                conn.close()

        converted_ts = self.convert_timestamp_ms_to_local_iso(ts_ms)

        if not found_row:
            self.status_message.emit(f"No telemetry row found for timestamp {converted_ts}. Annotation not deleted.")
            self.message_box_requested.emit("Deletion Failed", f"No telemetry row found for timestamp {converted_ts}. Annotation not deleted.", QMessageBox.Icon.Warning, False)
            return

        if not has_annotation:
            self.status_message.emit(f"No annotation found at timestamp {converted_ts} to delete.")
            self.message_box_requested.emit("No Annotation", f"No annotation found at timestamp {converted_ts} to delete.", QMessageBox.Icon.Warning, False)
            return

        if deleted:
            self.status_message.emit(f"Annotation deleted at timestamp {converted_ts}.")
            self.message_box_requested.emit("Annotation Deleted", f"Annotation deleted at timestamp {converted_ts}.", QMessageBox.Icon.Information, False)
            self.update_configuration_requested.emit()  # Trigger plot refresh to show annotation markers
        else:
            self.status_message.emit(f"No telemetry row found for timestamp {converted_ts}. Annotation not deleted.")
            self.message_box_requested.emit("Deletion Failed", f"No telemetry row found for timestamp {converted_ts}. Annotation not deleted.", QMessageBox.Icon.Warning, False)

    def convert_timestamp_ms_to_local_iso(self, ts_ms: int) -> str:
        """Convert a timestamp in milliseconds to a local ISO 8601 string"""
        try:
            dt_utc = dt.datetime.fromtimestamp(ts_ms / 1000.0, tz=dt.timezone.utc)
            dt_local = dt_utc.astimezone()
            return dt_local.isoformat()
        except Exception:
            return ""

    @staticmethod
    def _is_valid_telemetry_db(db_path: Path) -> bool:
        """Check if DB contains the expected telemetry table"""
        try:
            conn = sqlite3.connect(db_path)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='telemetry'"
                )
                return cursor.fetchone() is not None
            finally:
                conn.close()
        except Exception:
            return False

    @staticmethod
    def _sanitize_log_name(log_name: str) -> str:
        """Return a filesystem-safe log name"""
        raw = (log_name or "telemetry_log").strip()
        allowed = "-_"
        safe = "".join(ch for ch in raw if ch.isalnum() or ch in allowed)
        return safe or "telemetry_log"

    @staticmethod
    def _read_settings_file() -> configparser.ConfigParser:
        """Load settings from config/settings.ini"""
        config_path = resource_path("config/settings.ini")
        config = configparser.ConfigParser()
        config.read(str(config_path))
        return config
