"""
PlotWidget for plotting representation of the EvoFlow system and its components

Project: EvoFlow Innosuisse
Author: Patipol Thanuphol, Scientific Researcher at ZHAW — thau@zhaw.ch | patipol.thanuphol@zhaw.ch
Created: April 2026
"""

import time
import os
import configparser
import datetime as dt
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from matplotlib.ticker import ScalarFormatter
from matplotlib.ticker import FormatStrFormatter
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from PySide6.QtWidgets import QApplication, QHBoxLayout, QMainWindow, QMessageBox, QScrollBar, QWidget, QVBoxLayout, QLCDNumber, QLineEdit, QComboBox, QCalendarWidget, QTextEdit, QTimeEdit, QSizePolicy, QFileDialog
from PySide6.QtWidgets import QPushButton, QGroupBox, QTabWidget, QTableView, QMenuBar, QStatusBar, QLabel, QCheckBox, QColorDialog
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import Qt, QFile, QTimer, QDate, QTime, QIODeviceBase, QEvent, Signal, Slot, QObject
from PySide6.QtGui import QKeyEvent, QTextCharFormat, QStandardItemModel, QStandardItem, QWheelEvent, QCloseEvent, QAction, QPixmap, QColor, QPalette

from controlEntity.utils import resource_path


class PlotWidget(QWidget):
    """Widget for plotting required data from the evoflow system and sample extraction unit"""

    start_logging_requested = Signal(str, str, int)
    stop_logging_requested = Signal()
    timespan_minutes_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.connect_signals()
        self._on_update_configuration_clicked()
        # self.test_data_plot()

    def setup_ui(self):
        """Build the plotting canvas (3 stacked subplots with additional horizontal scrollbar at the bottom) and control panel, using settings.ini defaults"""
        
        button_style = """QPushButton {
                            background-color: #ffb765;
                            color: black;
                            border: 1px solid #ff8800;
                            border-radius: 4px; }
                            QPushButton:hover {
                                background-color: #fd9621; }
                            QPushButton:pressed {
                                background-color: #ce6e00; }
                            QPushButton:disabled {
                                background-color: #d9d9d9;
                                color: #888888; 
                                border: 1px solid #cccccc;} 
                            """

        groupbox_style = """QGroupBox {
                            font-weight: bold;
                            font-size: 14px;
                            color: #ffffff;
                            border: 2px solid '#ffffff';
                            border-radius: 10px;
                            margin-top: 10px;
                            background-color: '#252525';
                        }
                        QGroupBox::title {
                            subcontrol-origin: margin;
                            subcontrol-position: top center;
                            padding: 0px 3px;
                        }
                        """

        edit_style = """QLineEdit {
                        background-color: #5c5c5c;
                        color: White;
                        border-radius: 4px; }
                        QLineEdit:hover {
                            background-color: #737373;
                            color: White; }
                        QLineEdit:focus {
                            background-color: #d6d6d6;
                            color: Black; }
                        QLineEdit:disabled {
                            background-color: #d9d9d9;
                            color: #888888; } 
                        """
        
        text_style = """QLabel {
                        color: '#ffffff';
                        }"""
        
        scrollbar_style = """QScrollBar:horizontal {
                            background-color: #5c5c5c;
                            height: 20px;
                            margin: 0px 0px 0px 0px;
                            border-radius: 4px; }
                            QScrollBar::handle:horizontal {
                                background-color: #ffb765;
                                min-width: 20px;
                                border-radius: 4px; }
                            QScrollBar::handle:horizontal:hover {
                                background-color: #fd9621; }
                            QScrollBar::handle:horizontal:pressed {
                                background-color: #ce6e00; }
                            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                                background: none; }
                            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                                background: none; }"""
        
        config = self.read_settings_file()
        self.timespan_minutes = config.getint("plotConfiguration", "timespan_minutes", fallback=10)
        self.sampling_time_seconds = config.getint("plotConfiguration", "sampling_time_seconds", fallback=5)
        self.y_axis_od_min = config.getfloat("plotConfiguration", "y_axis_od_min", fallback=0)
        self.y_axis_od_max = config.getfloat("plotConfiguration", "y_axis_od_max", fallback=2.0)
        self.y_axis_phtCount_min = config.getfloat("plotConfiguration", "y_axis_phtCount_min", fallback=0)
        self.y_axis_phtCount_max = config.getfloat("plotConfiguration", "y_axis_phtCount_max", fallback=1000)
        self.y_axis_temp_min = config.getfloat("plotConfiguration", "y_axis_temp_min", fallback=30)
        self.y_axis_temp_max = config.getfloat("plotConfiguration", "y_axis_temp_max", fallback=40)
        self.y_axis_flowRate_min = config.getfloat("plotConfiguration", "y_axis_flowRate_min", fallback=0)
        self.y_axis_flowRate_max = config.getfloat("plotConfiguration", "y_axis_flowRate_max", fallback=10)
        self.scrollbar_max_loading_value = config.getint("plotConfiguration", "scrollbar_max_loading_value", fallback=2500)

        self._data_logging_active = False

        # ===============================
        # Plot section
        # ===============================
        self.plot_section_widget = QWidget(self)

        def style_axis(axis):
            """Apply a consistent dark-theme style to axis border, labels, and ticks"""
            axis.set_facecolor("none")
            if axis is not self.ax2:
                axis.tick_params(axis="x", colors="#e9e9e9", bottom=False, top=False)
            else:
                axis.tick_params(axis="x", colors="#e9e9e9", bottom=True, top=False)
            axis.tick_params(axis="y", colors="#e9e9e9")
            axis.grid(color="#636363", linestyle="--", linewidth=0.5, alpha=0.7)
            axis.xaxis.label.set_color("#ffffff")
            axis.yaxis.label.set_color("#ffffff")
            for spine in axis.spines.values():
                spine.set_edgecolor("#636363")

        def style_line(axis, label, color, style = "-", linewidth = 2.0, opacity = 1.0):
            """Create a rounded line style so corners appear smoother"""
            line, = axis.plot(
                [],
                [],
                label=label,
                color=color,
                alpha=opacity,
                linewidth=linewidth,
                linestyle=style,
                solid_joinstyle="round",
                solid_capstyle="round",
                antialiased=True,
            )
            return line

        self.fig, (self.ax0, self.ax1, self.ax2) = plt.subplots(3, 1)
        self.fig.suptitle("EvoFlow Data Visualization", color="white", fontweight="bold")

        # First subplot: flow rate, phtCount
        self.ax0.set_xticklabels([])    # remove the x-axis ticks and labels
        # Flow Rate on left y-axis
        self.ax0.set_ylabel("Flow Rate\n(mL/min)", color="white")
        self.ax0.yaxis.set_label_coords(-0.045, 0.5)  # Move y-axis label to the left
        self.ax0.set_ylim(self.y_axis_flowRate_min, self.y_axis_flowRate_max)
        # self.ax0.yaxis.set_major_formatter(FormatStrFormatter('%.1f'))  # Format y-axis ticks to 1 decimal place
        style_axis(self.ax0)
        self.flowRate_pump1 = style_line(self.ax0, "Flow Rate", "lime", style="-.", opacity=1.0)
        self.flowRate_pump2 = style_line(self.ax0, "Flow Rate Lagoon", "cyan", style="-.", opacity=1.0)
        self.flowRate_pump1_sp = style_line(self.ax0, "Flow Rate Pump 1 Setpoint", "lime", style="-", linewidth=0.5, opacity=0.7)
        self.flowRate_pump2_sp = style_line(self.ax0, "Flow Rate Pump 2 Setpoint", "cyan", style="-", linewidth=0.5, opacity=0.7)
        # phtCount on right y-axis
        self.ax0_r = self.ax0.twinx()
        self.ax0_r.set_ylabel("Photon Count\n(MHz)", color="white")
        self.ax0_r.yaxis.set_label_coords(1.045, 0.5)  # Move y-axis label to the right
        self.ax0_r.set_ylim(self.y_axis_phtCount_min, self.y_axis_phtCount_max)
        style_axis(self.ax0_r)
        self.phtCount_lagoon = style_line(self.ax0_r, "phtCount", "red", style="-", opacity=1.0)

        # Second subplot: Temperature, OD
        self.ax1.set_xticklabels([])    # remove the x-axis ticks and labels
        # Temperature on left y-axis
        self.ax1.set_ylabel("Temperature\n(°C)")
        self.ax1.yaxis.set_label_coords(-0.045, 0.5)  # Move y-axis label to the left
        self.ax1.set_ylim(self.y_axis_temp_min, self.y_axis_temp_max)
        style_axis(self.ax1)
        self.temp_bioReactor = style_line(self.ax1, "Temp", "orange", style="-.", opacity=1.0)
        self.temp_lagoon = style_line(self.ax1, "Temp Lagoon", "yellow", style="-.", opacity=1.0)
        self.temp_bioReactor_sp = style_line(self.ax1, "Temp Bioreactor Setpoint", "orange", style="-", linewidth=0.5, opacity=0.7)
        self.temp_lagoon_sp = style_line(self.ax1, "Temp Lagoon Setpoint", "yellow", style="-", linewidth=0.5, opacity=0.7)
        # OD on right y-axis
        self.ax1_r = self.ax1.twinx()
        self.ax1_r.set_ylabel("Optical Density\n(OD)")
        self.ax1_r.yaxis.set_label_coords(1.045, 0.5)  # Move y-axis label to the right
        self.ax1_r.set_ylim(self.y_axis_od_min, self.y_axis_od_max)
        style_axis(self.ax1_r)
        self.od_bioReactor = style_line(self.ax1_r, "OD", "tan", style="-", opacity=1.0)
        self.od_lagoon = style_line(self.ax1_r, "OD Lagoon", "white", style="-", opacity=1.0)

        # Third subplot: scatter plot for the event when sample extraction takes a sample
        self.ax2.set_ylabel("SE\nEvent")
        self.ax2.yaxis.set_label_coords(-0.045, 0.5)  # Move y-axis label to the left
        self.ax2.set_yticks([])
        self.ax2.set_yticklabels([])
        self.ax2.set_ylim(0.9, 1.1)
        self.ax2.xaxis.set_major_formatter(FuncFormatter(self._format_unix_seconds_as_datetime))
        # self.ax2.set_xlabel("Date / Time")
        style_axis(self.ax2)
        self.sample_extraction_events, = self.ax2.plot([], [], label="Sample Extraction", marker="o", linestyle="", color="magenta", markersize=10)

        # Remove Matplotlib's default horizontal data padding.
        self.ax0.margins(x=0)
        self.ax0_r.margins(x=0)
        self.ax1.margins(x=0)
        self.ax1_r.margins(x=0)
        self.ax2.margins(x=0)

        # Set initial x-axis limits
        now_s = time.time()
        window_s = float(self.timespan_minutes * 60)
        x_min = now_s - window_s
        x_max = now_s
        self.ax0.set_xlim(x_min, x_max)
        self.ax0_r.set_xlim(x_min, x_max)
        self.ax1.set_xlim(x_min, x_max)
        self.ax1_r.set_xlim(x_min, x_max)
        self.ax2.set_xlim(x_min, x_max)

        # -------------------------------
        # Canvas geometry (Matplotlib)
        # -------------------------------
        # tight_layout computes spacing for titles/labels so text is not clipped.
        # We call it first, then pin subplot rectangles with set_position(...) to keep
        # your custom visual ratio stable across window sizes.
        self.fig.tight_layout()
        self.fig.set_facecolor('#252525')
        self.canvas = FigureCanvas(self.fig)
        # Expanding policy: when Qt gives extra space, the canvas grows with it.
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Subplot rectangles in normalized figure coordinates [left, bottom, width, height].
        # These values preserve the same relative layout while scaling with canvas size.
        self.ax0.set_position([0.07, 0.59, 0.860, 0.33])
        self.ax1.set_position([0.07, 0.22, 0.860, 0.33])
        self.ax2.set_position([0.07, 0.1, 0.860, 0.08])


        # -------------------------------
        # Scrollbar row (Qt)
        # -------------------------------
        # This row is fixed-height so only the canvas consumes extra vertical space.
        self.scrollbar_ax = QScrollBar(Qt.Horizontal, self)
        self.scrollbar_ax.setMinimumHeight(20)
        self.scrollbar_ax.setMinimum(0)
        self.scrollbar_ax.setStyleSheet(scrollbar_style)
        self.scrollbar_ax.setMaximum(self.timespan_minutes * 60)
        self.scrollbar_ax.setPageStep(self.sampling_time_seconds)
        self.scrollbar_ax.setSingleStep(self.sampling_time_seconds)
        self.scrollbar_ax.setValue(self.timespan_minutes * 60)  # Start at the end of the timespan

        self.scrollbar_row_widget = QWidget(self.plot_section_widget)
        self.scrollbar_row_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.scrollbar_row_widget.setFixedHeight(22)
        self.scrollbar_row_layout = QHBoxLayout(self.scrollbar_row_widget)
        self.scrollbar_row_layout.setContentsMargins(0, 0, 0, 0)
        self.scrollbar_row_layout.setSpacing(0)
        self.scrollbar_row_layout.addWidget(self.scrollbar_ax)


        # -------------------------------
        # Plot area container layout
        # -------------------------------
        self.plot_section_widget_layout = QVBoxLayout(self.plot_section_widget)
        self.plot_section_widget_layout.setContentsMargins(0, 0, 0, 0)
        self.plot_section_widget_layout.setSpacing(4)
        # Stretch factor 1 means this widget takes all remaining height.
        self.plot_section_widget_layout.addWidget(self.canvas, 1)
        # Stretch factor 0 keeps this row at its size hint / fixed height.
        self.plot_section_widget_layout.addWidget(self.scrollbar_row_widget, 0)

        # Keep scrollbar width/position aligned with the drawable area of ax2.
        self.canvas.mpl_connect("draw_event", lambda _event: self._sync_scrollbar_to_ax2())
        QTimer.singleShot(0, self._sync_scrollbar_to_ax2)

        # ===============================
        # Control panel section
        # ===============================
        control_panel_section_widget = QWidget(self)
        control_panel_layout = QVBoxLayout()

        configuration_group = QGroupBox("Plot Configuration")
        configuration_group.setStyleSheet(groupbox_style)
        configuration_layout = QVBoxLayout(configuration_group)
        configuration_first_row_layout = QHBoxLayout()
        configuration_second_row_layout = QHBoxLayout()
        configuration_third_row_layout = QHBoxLayout()
        configuration_forth_row_layout = QHBoxLayout()
        configuration_fifth_row_layout = QHBoxLayout()

        timespan = QLabel(f"Timespan (minutes):")
        timespan.setStyleSheet(text_style)
        self.timespan_edit= QLineEdit(str(self.timespan_minutes))
        self.timespan_edit.setStyleSheet(edit_style)
        sampling_time = QLabel(f"Sampling Time (seconds):")
        sampling_time.setStyleSheet(text_style)
        self.sampling_time_edit = QLineEdit(str(self.sampling_time_seconds))
        self.sampling_time_edit.setStyleSheet(edit_style)
        y_axis_flowRate_min = QLabel(f"Y-axis Flow Rate Min:")
        y_axis_flowRate_min.setStyleSheet(text_style)
        self.y_axis_flowRate_min_edit = QLineEdit(str(self.y_axis_flowRate_min))
        self.y_axis_flowRate_min_edit.setStyleSheet(edit_style)
        y_axis_flowRate_max = QLabel(f"Y-axis Flow Rate Max:")
        y_axis_flowRate_max.setStyleSheet(text_style)
        self.y_axis_flowRate_max_edit = QLineEdit(str(self.y_axis_flowRate_max))
        self.y_axis_flowRate_max_edit.setStyleSheet(edit_style)
        y_axis_phtCount_min = QLabel(f"Y-axis phtCount Min:")
        y_axis_phtCount_min.setStyleSheet(text_style)
        self.y_axis_phtCount_min_edit = QLineEdit(str(self.y_axis_phtCount_min))
        self.y_axis_phtCount_min_edit.setStyleSheet(edit_style)
        y_axis_phtCount_max = QLabel(f"Y-axis phtCount Max:")
        y_axis_phtCount_max.setStyleSheet(text_style)
        self.y_axis_phtCount_max_edit = QLineEdit(str(self.y_axis_phtCount_max))
        self.y_axis_phtCount_max_edit.setStyleSheet(edit_style)
        y_axis_temp_min = QLabel(f"Y-axis Temp Min:")
        y_axis_temp_min.setStyleSheet(text_style)
        self.y_axis_temp_min_edit = QLineEdit(str(self.y_axis_temp_min))
        self.y_axis_temp_min_edit.setStyleSheet(edit_style)
        y_axis_temp_max = QLabel(f"Y-axis Temp Max:")
        y_axis_temp_max.setStyleSheet(text_style)
        self.y_axis_temp_max_edit = QLineEdit(str(self.y_axis_temp_max))
        self.y_axis_temp_max_edit.setStyleSheet(edit_style)
        y_axis_od_min = QLabel(f"Y-axis OD Min:")
        y_axis_od_min.setStyleSheet(text_style)
        self.y_axis_od_min_edit = QLineEdit(str(self.y_axis_od_min))
        self.y_axis_od_min_edit.setStyleSheet(edit_style)
        y_axis_od_max = QLabel(f"Y-axis OD Max:")
        y_axis_od_max.setStyleSheet(text_style)
        self.y_axis_od_max_edit = QLineEdit(str(self.y_axis_od_max))
        self.y_axis_od_max_edit.setStyleSheet(edit_style)

        configuration_first_row_layout.addWidget(timespan)
        configuration_first_row_layout.addWidget(self.timespan_edit)
        configuration_first_row_layout.addWidget(sampling_time)
        configuration_first_row_layout.addWidget(self.sampling_time_edit)
        configuration_second_row_layout.addWidget(y_axis_flowRate_min)
        configuration_second_row_layout.addWidget(self.y_axis_flowRate_min_edit)
        configuration_second_row_layout.addWidget(y_axis_flowRate_max)
        configuration_second_row_layout.addWidget(self.y_axis_flowRate_max_edit)
        configuration_third_row_layout.addWidget(y_axis_phtCount_min)
        configuration_third_row_layout.addWidget(self.y_axis_phtCount_min_edit)
        configuration_third_row_layout.addWidget(y_axis_phtCount_max)
        configuration_third_row_layout.addWidget(self.y_axis_phtCount_max_edit)
        configuration_forth_row_layout.addWidget(y_axis_temp_min)
        configuration_forth_row_layout.addWidget(self.y_axis_temp_min_edit)
        configuration_forth_row_layout.addWidget(y_axis_temp_max)
        configuration_forth_row_layout.addWidget(self.y_axis_temp_max_edit)
        configuration_fifth_row_layout.addWidget(y_axis_od_min)
        configuration_fifth_row_layout.addWidget(self.y_axis_od_min_edit)
        configuration_fifth_row_layout.addWidget(y_axis_od_max)
        configuration_fifth_row_layout.addWidget(self.y_axis_od_max_edit)

        configuration_layout.addLayout(configuration_first_row_layout)
        configuration_layout.addLayout(configuration_second_row_layout)
        configuration_layout.addLayout(configuration_third_row_layout)
        configuration_layout.addLayout(configuration_forth_row_layout)
        configuration_layout.addLayout(configuration_fifth_row_layout)

        self.update_config_button = QPushButton("Update Configuration")
        self.update_config_button.setStyleSheet(button_style)
        self.update_config_button.setMinimumHeight(40)
        self.update_config_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        configuration_layout.addWidget(self.update_config_button)
        configuration_layout.addStretch(1)  # Push the button to the top
        
        # -------------------------------
        # Data logging group
        # -------------------------------
        data_logging_group = QGroupBox("Data Logging")
        data_logging_group.setStyleSheet(groupbox_style)
        data_logging_layout = QVBoxLayout(data_logging_group)

        data_logging_first_row_layout = QHBoxLayout()
        data_logging_second_row_layout = QHBoxLayout()
        data_logging_third_row_layout = QHBoxLayout()
        data_logging_forth_row_layout = QHBoxLayout()

        log_name = QLabel("Log Name:")
        log_name.setStyleSheet(text_style)
        self.log_name_edit = QLineEdit("evoflow_telemetry")
        self.log_name_edit.setStyleSheet(edit_style)
        self.browse_location_button = QPushButton("Browse")
        self.browse_location_button.setStyleSheet(button_style)
        self.browse_location_button.setMinimumWidth(60)
        log_location = QLabel("Log Location:")
        log_location.setStyleSheet(text_style)
        self.log_location_label = QLabel(str(os.path.join(os.getcwd(), "logs")))
        self.log_location_label.setStyleSheet(text_style)
        self.log_location_label.setMinimumWidth(200)
        self.log_location_label.setMaximumWidth(450)
        self.log_location_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.start_logging_button = QPushButton("Start Logging")
        self.start_logging_button.setStyleSheet(button_style)
        self.start_logging_button.setMinimumHeight(40)
        self.start_logging_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.stop_logging_button = QPushButton("Stop Logging")
        self.stop_logging_button.setStyleSheet(button_style)
        self.stop_logging_button.setMinimumHeight(40)
        self.stop_logging_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.stop_logging_button.setEnabled(False)
        self.open_log_button = QPushButton("Open Logged Data")
        self.open_log_button.setStyleSheet(button_style)
        self.open_log_button.setMinimumHeight(40)
        self.open_log_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.export_log_button = QPushButton("Export Log to CSV")
        self.export_log_button.setStyleSheet(button_style)
        self.export_log_button.setMinimumHeight(40)
        self.export_log_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)


        data_logging_first_row_layout.addWidget(log_name)
        data_logging_first_row_layout.addWidget(self.log_name_edit)
        data_logging_second_row_layout.addWidget(log_location)
        data_logging_second_row_layout.addWidget(self.log_location_label)
        data_logging_second_row_layout.addWidget(self.browse_location_button)
        data_logging_third_row_layout.addWidget(self.start_logging_button)
        data_logging_third_row_layout.addWidget(self.stop_logging_button)
        data_logging_forth_row_layout.addWidget(self.open_log_button)
        data_logging_forth_row_layout.addWidget(self.export_log_button)

        data_logging_layout.addLayout(data_logging_first_row_layout)
        data_logging_layout.addLayout(data_logging_second_row_layout)
        data_logging_layout.addLayout(data_logging_third_row_layout)
        data_logging_layout.addLayout(data_logging_forth_row_layout)
        data_logging_layout.addStretch(1)  # Push the buttons to the top

        # Add groups to control panel layout
        control_panel_layout.addWidget(configuration_group)
        control_panel_layout.addWidget(data_logging_group)
        control_panel_section_widget.setLayout(control_panel_layout)

        # Main widget split: plot area takes ~3/4 width, control panel ~1/4.
        layout = QHBoxLayout(self)
        layout.addWidget(self.plot_section_widget, stretch=3)
        layout.addWidget(control_panel_section_widget, stretch=1)

    def connect_signals(self):
        """Wire local PlotWidget controls to slots/signals"""
        self.update_config_button.clicked.connect(self._on_update_configuration_clicked)
        self.start_logging_button.clicked.connect(self._on_start_logging_clicked)
        self.stop_logging_button.clicked.connect(self.stop_logging_requested)
        self.browse_location_button.clicked.connect(self._on_browse_location_clicked)

    def _on_update_configuration_clicked(self):
        """Changing plot configuration parameters and replotting with new settings"""
        self.timespan_minutes = max(1, self._safe_int(self.timespan_edit, self.timespan_minutes))
        self.timespan_minutes_changed.emit(self.timespan_minutes)
        self.sampling_time_seconds = max(1, self._safe_int(self.sampling_time_edit, self.sampling_time_seconds))

        self.y_axis_flowRate_min = self._safe_float(self.y_axis_flowRate_min_edit, self.y_axis_flowRate_min)
        self.y_axis_flowRate_max = self._safe_float(self.y_axis_flowRate_max_edit, self.y_axis_flowRate_max)
        self.y_axis_phtCount_min = self._safe_float(self.y_axis_phtCount_min_edit, self.y_axis_phtCount_min)
        self.y_axis_phtCount_max = self._safe_float(self.y_axis_phtCount_max_edit, self.y_axis_phtCount_max)
        self.y_axis_temp_min = self._safe_float(self.y_axis_temp_min_edit, self.y_axis_temp_min)
        self.y_axis_temp_max = self._safe_float(self.y_axis_temp_max_edit, self.y_axis_temp_max)
        self.y_axis_od_min = self._safe_float(self.y_axis_od_min_edit, self.y_axis_od_min)
        self.y_axis_od_max = self._safe_float(self.y_axis_od_max_edit, self.y_axis_od_max)

        self.ax0.set_ylim(self.y_axis_flowRate_min, self.y_axis_flowRate_max)
        self.ax0_r.set_ylim(self.y_axis_phtCount_min, self.y_axis_phtCount_max)
        self.ax1.set_ylim(self.y_axis_temp_min, self.y_axis_temp_max)
        self.ax1_r.set_ylim(self.y_axis_od_min, self.y_axis_od_max)

        self.scrollbar_ax.setMaximum(self.timespan_minutes * 60)
        self.scrollbar_ax.setPageStep(self.sampling_time_seconds * 3)
        self.scrollbar_ax.setSingleStep(self.sampling_time_seconds)
        self.scrollbar_ax.setValue(self.timespan_minutes * 60)
        
        self.canvas.draw_idle()

    def clear_plots(self):
        """Clear all plotted data series"""
        self.flowRate_pump1.set_data([], [])
        self.flowRate_pump2.set_data([], [])
        self.phtCount_lagoon.set_data([], [])
        self.temp_bioReactor.set_data([], [])
        self.temp_lagoon.set_data([], [])
        self.od_bioReactor.set_data([], [])
        self.od_lagoon.set_data([], [])
        self.sample_extraction_events.set_data([], [])
        self.canvas.draw_idle()

    def _on_start_logging_clicked(self):
        """Emit start-logging request using current UI parameters"""
        sampling_time_seconds = self._safe_int(self.sampling_time_edit, self.sampling_time_seconds)
        log_name = self.log_name_edit.text().strip()
        log_directory = self.log_location_label.text().strip()
        self.start_logging_requested.emit(log_name, log_directory, sampling_time_seconds)

    def _on_browse_location_clicked(self):
        """Browse and set data log target directory"""
        selected_dir = QFileDialog.getExistingDirectory(self, "Select Log Directory", self.log_location_label.text().strip() or os.getcwd())
        if selected_dir:
            self.log_location_label.setText(selected_dir)

    @Slot(dict, int)
    def update_plot_from_logged_data(self, payload: dict, total_data_points: int):
        """Update plotted series from logging worker payload"""
        x_values = payload.get("x_seconds", [])
        if not x_values:
            return

        self.flowRate_pump1.set_data(x_values, payload.get("flow_rate_pump1", []))
        self.flowRate_pump2.set_data(x_values, payload.get("flow_rate_pump2", []))
        self.phtCount_lagoon.set_data(x_values, payload.get("pht_count_lagoon", []))
        self.temp_bioReactor.set_data(x_values, payload.get("temp_bioreactor", []))
        self.temp_lagoon.set_data(x_values, payload.get("temp_lagoon", []))
        self.temp_bioReactor_sp.set_data(x_values, payload.get("temp_bioreactor_sp", []))
        self.temp_lagoon_sp.set_data(x_values, payload.get("temp_lagoon_sp", []))
        self.od_bioReactor.set_data(x_values, payload.get("od_bioreactor", []))
        self.od_lagoon.set_data(x_values, payload.get("od_lagoon", []))
        self.sample_extraction_events.set_data(x_values, payload.get("sample_event", []))
        self.update_x_axis()
        self.canvas.draw_idle()

        # scrollbar management
        # the scrollbar should handle at maximum the number defined in the settings file.
        # but for the update purpose, the maximum value grows with the number of data points we have.
        if total_data_points > self.scrollbar_max_loading_value:
            self.scrollbar_ax.setMaximum(self.scrollbar_max_loading_value)
            self.scrollbar_ax.setValue(self.scrollbar_max_loading_value)
        else:
            self.scrollbar_ax.setMaximum(total_data_points)
            self.scrollbar_ax.setValue(total_data_points)

    def update_x_axis(self):
        """Update x-axis limits based on current time and timespan, keeping the same range of x-values visible"""
        # X here is the time in the form of Unix timestamp seconds
        # Because we defined the function to turn time in Unix timestamp seconds to date/time string for x-axis tick labels,
        # we can directly use the current Unix timestamp seconds to set the x-axis limits, and the tick labels will automatically show the corresponding date/time.        
        x_min, x_max = self.ax0.get_xlim()
        if self._data_logging_active:
            now_s = time.time()
            window_s = float(self.timespan_minutes * 60)
            x_min = now_s - window_s
            x_max = now_s

        self.ax0.set_xlim(x_min, x_max)
        self.ax0_r.set_xlim(x_min, x_max)
        self.ax1.set_xlim(x_min, x_max)
        self.ax1_r.set_xlim(x_min, x_max)
        self.ax2.set_xlim(x_min, x_max)
        
    @Slot(bool)
    def set_logging_state(self, is_logging: bool):
        """Reflect active logging state in UI controls"""
        self._data_logging_active = is_logging
        # Disabling Sampling Time edit, log name edit, and browse button during active logging
        self.sampling_time_edit.setEnabled(not is_logging)
        self.log_name_edit.setEnabled(not is_logging)
        self.browse_location_button.setEnabled(not is_logging)
        self.start_logging_button.setEnabled(not is_logging)
        self.stop_logging_button.setEnabled(is_logging)

    @Slot(str)
    def show_status_message(self, message: str):
        """Show worker status in widget tooltip and stdout for debugging"""
        self.setToolTip(message)
        print(message)

    @staticmethod
    def _safe_int(line_edit: QLineEdit, fallback: int) -> int:
        """Parse int from line edit, fallback if invalid"""
        try:
            return int(line_edit.text().strip())
        except Exception:
            line_edit.setText(str(fallback))
            return int(fallback)

    @staticmethod
    def _safe_float(line_edit: QLineEdit, fallback: float) -> float:
        """Parse float from line edit, fallback if invalid"""
        try:
            return float(line_edit.text().strip())
        except Exception:
            line_edit.setText(str(fallback))
            return float(fallback)

    @staticmethod
    def _format_unix_seconds_as_datetime(x_value: float, _position: int) -> str:
        """Format Unix timestamp seconds as date/time for x-axis tick labels"""
        try:
            timestamp = float(x_value)
            return dt.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d\n%H:%M:%S")
        except Exception:
            return ""

    def read_settings_file(self):
        """Load plotting defaults from config/settings.ini"""
        config_path = resource_path("config/settings.ini")
        config = configparser.ConfigParser()
        config.read(str(config_path))
        return config

    def _sync_scrollbar_to_ax2(self):
        """Match the scrollbar width and horizontal offset to ax2's plotting area"""
        if not hasattr(self, "ax2") or not hasattr(self, "canvas"):
            return

        ax2_pos = self.ax2.get_position()
        canvas_width = self.canvas.width()

        if canvas_width <= 0:
            return

        # Convert normalized axis geometry (0..1) into current canvas pixels.
        left_px = max(0, int(ax2_pos.x0 * canvas_width))
        width_px = max(1, int(ax2_pos.width * canvas_width))
        right_px = max(0, canvas_width - (left_px + width_px))

        self.scrollbar_ax.setFixedWidth(width_px)
        self.scrollbar_row_layout.setContentsMargins(left_px, 0, right_px, 0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QTimer.singleShot(0, self._sync_scrollbar_to_ax2)

    def test_data_plot(self):
        """Plot some test data to verify the plotting functionality"""
        import numpy as np
        now_s = time.time()
        x_data = np.arange(
            now_s - (self.timespan_minutes * 60),
            now_s + self.sampling_time_seconds,
            self.sampling_time_seconds,
        )
        od_bioReactor_data = np.random.uniform(0.5, 0.8, size=len(x_data))
        od_lagoon_data = np.random.uniform(0.8, 1.0, size=len(x_data))
        phtCount_lagoon_data = np.random.uniform(100, 120, size=len(x_data))
        temp_bioReactor_data = np.random.uniform(36.7, 36.9, size=len(x_data))
        temp_lagoon_data = np.random.uniform(37.0, 37.3, size=len(x_data))
        flowRate_pump1_data = np.random.uniform(0.5, 2.5, size=len(x_data))
        flowRate_pump2_data = np.random.uniform(1.8, 2.2, size=len(x_data))
        sample_extraction_events_data = np.random.choice([0, 1], size=len(x_data), p=[0.9, 0.1])

        self.od_bioReactor.set_data(x_data, od_bioReactor_data)
        self.od_lagoon.set_data(x_data, od_lagoon_data)
        self.phtCount_lagoon.set_data(x_data, phtCount_lagoon_data)
        self.temp_bioReactor.set_data(x_data, temp_bioReactor_data)
        self.temp_lagoon.set_data(x_data, temp_lagoon_data)
        self.flowRate_pump1.set_data(x_data, flowRate_pump1_data)
        self.flowRate_pump2.set_data(x_data, flowRate_pump2_data)
        self.sample_extraction_events.set_data(x_data, sample_extraction_events_data)

        # Keep all shared x-axes synchronized with incoming data range.
        x_min = float(x_data[0])
        x_max = float(x_data[-1])
        self.ax0.set_xlim(x_min, x_max)
        self.ax0_r.set_xlim(x_min, x_max)
        self.ax1.set_xlim(x_min, x_max)
        self.ax1_r.set_xlim(x_min, x_max)
        self.ax2.set_xlim(x_min, x_max)

        self.canvas.draw()
