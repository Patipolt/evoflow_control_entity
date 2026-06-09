"""
Background worker for telemetry logging and history retrieval.

Stores telemetry in rotated SQLite files and serves timespan-bounded data for PlotWidget.
"""

from __future__ import annotations

import configparser
import copy
import datetime as dt
import os
import sqlite3
import time
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QTimer, Signal, Slot

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
        self._timespan_minutes = 0

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

    @Slot(int)
    def set_timespan_minutes(self, timespan_minutes: int):
        """Update current plot timespan window"""
        self._timespan_minutes = max(1, int(timespan_minutes))
        # Update plot data immediately to reflect new timespan setting
        self.plot_data_updated.emit(self._load_plot_data(self._timespan_minutes), self._count_total_logged_rows())

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
            float(evoflow_snapshot.get("pump_1_sp", 0.0)),
            float(evoflow_snapshot.get("pump_1_speed", 0.0)),
            int(evoflow_snapshot.get("pump_2_status", 0)),
            float(evoflow_snapshot.get("pump_2_sp", 0.0)),
            float(evoflow_snapshot.get("pump_2_speed", 0.0)),
            int(evoflow_snapshot.get("pump_3_status", 0)),
            float(evoflow_snapshot.get("pump_3_sp", 0.0)),
            float(evoflow_snapshot.get("pump_3_speed", 0.0)),
            int(evoflow_snapshot.get("pump_4_status", 0)),
            float(evoflow_snapshot.get("pump_4_sp", 0.0)),
            float(evoflow_snapshot.get("pump_4_speed", 0.0)),
            int(evoflow_snapshot.get("magneticStirrer_bioreactor_status", 0)),
            float(evoflow_snapshot.get("magneticStirrer_bioreactor_sp", 0.0)),
            float(evoflow_snapshot.get("magneticStirrer_bioreactor_speed", 0.0)),
            float(evoflow_snapshot.get("magneticStirrer_bioreactor_fan_duty_cycle", 0.0)),
            int(evoflow_snapshot.get("magneticStirrer_lagoon_status", 0)),
            float(evoflow_snapshot.get("magneticStirrer_lagoon_sp", 0.0)),
            float(evoflow_snapshot.get("magneticStirrer_lagoon_speed", 0.0)),
            float(evoflow_snapshot.get("magneticStirrer_lagoon_fan_duty_cycle", 0.0)),
            int(evoflow_snapshot.get("valve_bio2lag_status", 0)),
            int(evoflow_snapshot.get("valve_sug2lag_status", 0)),
            int(evoflow_snapshot.get("od_bioreactor_status", 0)),
            float(evoflow_snapshot.get("od_bioreactor_value", 0.0)),
            int(evoflow_snapshot.get("od_lagoon_status", 0)),
            float(evoflow_snapshot.get("od_lagoon_value", 0.0)),
            int(evoflow_snapshot.get("tempCtrl_bioreactor_status", 0)),
            float(evoflow_snapshot.get("tempCtrl_bioreactor_sp", 0.0)),
            float(evoflow_snapshot.get("tempCtrl_bioreactor_heater_duty_cycle", 0.0)),
            float(evoflow_snapshot.get("phtCount_lagoon_value", 0.0)),
            float(evoflow_snapshot.get("tempCtrl_bioreactor_value", 0.0)),
            int(evoflow_snapshot.get("tempCtrl_lagoon_status", 0)),
            float(evoflow_snapshot.get("tempCtrl_lagoon_sp", 0.0)),
            float(evoflow_snapshot.get("tempCtrl_lagoon_value", 0.0)),
            float(evoflow_snapshot.get("tempCtrl_lagoon_heater_duty_cycle", 0.0)),
            int(evoflow_snapshot.get("phtCount_lagoon_status", 0)),
            int(evoflow_snapshot.get("phtCount_lagoon_overlight", 0)),
            float(flow_rate_1),
            float(flow_rate_2),
            float(flow_rate_3),
            float(flow_rate_4),
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
                tempCtrl_bioreactor_heater_duty_cycle,
                phtCount_lagoon_value,
                tempCtrl_bioreactor_value,
                tempCtrl_lagoon_status,
                tempCtrl_lagoon_sp,
                tempCtrl_lagoon_value,
                tempCtrl_lagoon_heater_duty_cycle,
                phtCount_lagoon_status,
                phtCount_lagoon_overlight,
                flow_rate_pump1,
                flow_rate_pump2,
                flow_rate_pump3,
                flow_rate_pump4,
                sample_row,
                sample_col,
                sample_done_flag
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            row,
        )
        self._conn.commit()

        self._row_count_current_db += 1
        if self._segment_start_ts_ms is None:
            self._segment_start_ts_ms = ts_ms
        self._segment_end_ts_ms = ts_ms

        if self._row_count_current_db >= self._max_rows_per_db:
            self._rotate_segment_db()

        all_data_points_logged = self._count_total_logged_rows()

        # Request updated plot data after each new log entry
        self.plot_data_updated.emit(self._load_plot_data(self._timespan_minutes), all_data_points_logged)
    
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
            """
            CREATE TABLE IF NOT EXISTS telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                tempCtrl_bioreactor_heater_duty_cycle REAL,
                phtCount_lagoon_value REAL,
                tempCtrl_bioreactor_value REAL,
                tempCtrl_lagoon_status INTEGER,
                tempCtrl_lagoon_sp REAL,
                tempCtrl_lagoon_value REAL,
                tempCtrl_lagoon_heater_duty_cycle REAL,
                phtCount_lagoon_status INTEGER,
                phtCount_lagoon_overlight INTEGER,
                flow_rate_pump1 REAL,
                flow_rate_pump2 REAL,
                flow_rate_pump3 REAL,
                flow_rate_pump4 REAL,
                sample_row INTEGER,
                sample_col INTEGER,
                sample_done_flag INTEGER
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

    def _load_plot_data(self, timespan_minutes: int) -> dict[str, list[float]]:
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
        }

        if self._session_dir is None:
            return payload

        db_files = sorted(self._session_dir.glob("telemetry_*.sqlite"))
        if not db_files:
            return payload

        cutoff_ms = int(time.time() * 1000) - (max(1, timespan_minutes) * 60 * 1000)
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
                        sample_done_flag
                    FROM telemetry
                    WHERE ts_unix_ms >= ?
                    ORDER BY ts_unix_ms ASC
                    """,
                    (cutoff_ms,),
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

        return payload

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
