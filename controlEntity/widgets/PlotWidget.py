"""
PlotWidget for plotting representation of the EvoFlow system and its components

Project: EvoFlow Innosuisse
Author: Patipol Thanuphol, Scientific Researcher at ZHAW — thau@zhaw.ch | patipol.thanuphol@zhaw.ch
Created: April 2026
"""

import time
import os
import configparser
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter
from matplotlib.ticker import FormatStrFormatter
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from PySide6.QtWidgets import QApplication, QHBoxLayout, QMainWindow, QMessageBox, QScrollBar, QWidget, QVBoxLayout, QLCDNumber, QLineEdit, QComboBox, QCalendarWidget, QTextEdit, QTimeEdit, QSizePolicy
from PySide6.QtWidgets import QPushButton, QGroupBox, QTabWidget, QTableView, QMenuBar, QStatusBar, QLabel, QCheckBox, QColorDialog
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import Qt, QFile, QTimer, QDate, QTime, QIODeviceBase, QEvent, Signal, Slot, QObject
from PySide6.QtGui import QKeyEvent, QTextCharFormat, QStandardItemModel, QStandardItem, QWheelEvent, QCloseEvent, QAction, QPixmap, QColor, QPalette

from controlEntity.utils import resource_path


class PlotWidget(QWidget):
    """Widget for plotting required data from the evoflow system and sample extraction unit"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.test_data_plot()

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
                                color: #888888; } 
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

        # ===============================
        # Plot section
        # ===============================
        self.plot_section_widget = QWidget(self)

        def style_axis(axis):
            """Apply a consistent dark-theme style to axis border, labels, and ticks."""
            axis.set_facecolor("none")
            if axis is not self.ax2:
                axis.tick_params(axis="x", colors="#e9e9e9", bottom=False, top=False)
            else:
                axis.tick_params(axis="x", colors="#e9e9e9", bottom=True, top=False)
            axis.tick_params(axis="y", colors="#e9e9e9")
            axis.xaxis.label.set_color("#ffffff")
            axis.yaxis.label.set_color("#ffffff")
            for spine in axis.spines.values():
                spine.set_edgecolor("#636363")

        def style_line(axis, label, color, style = "-", opacity = 1.0):
            """Create a rounded line style so corners appear smoother."""
            line, = axis.plot(
                [],
                [],
                label=label,
                color=color,
                alpha=opacity,
                linewidth=2.0,
                linestyle=style,
                solid_joinstyle="round",
                solid_capstyle="round",
                antialiased=True,
            )
            return line

        self.fig, (self.ax0, self.ax1, self.ax2) = plt.subplots(3, 1)
        self.fig.suptitle("EvoFlow Data Visualization", color="white", fontweight="bold")

        x_axis_ticks = [i for i in range(0, self.timespan_minutes * 60 + 1, self.sampling_time_seconds)]

        # First subplot: OD, phtCount
        self.ax0.set_xticklabels([])    # remove the x-axis ticks and labels
        # OD on left y-axis
        self.ax0.set_ylabel("Optical Density\n(OD)", color="white")
        self.ax0.yaxis.set_label_coords(-0.045, 0.5)  # Move y-axis label to the left
        self.ax0.set_ylim(self.y_axis_od_min, self.y_axis_od_max)
        # self.ax0.yaxis.set_major_formatter(FormatStrFormatter('%.1f'))  # Format y-axis ticks to 1 decimal place
        style_axis(self.ax0)
        self.od_bioReactor = style_line(self.ax0, "OD", "lightGreen", style=":", opacity=0.5)
        self.od_lagoon = style_line(self.ax0, "OD Lagoon", "cyan", style=":", opacity=0.5)
        # phtCount on right y-axis
        self.ax0_r = self.ax0.twinx()
        self.ax0_r.set_ylabel("Photon Count\n(MHz)", color="white")
        self.ax0_r.yaxis.set_label_coords(1.045, 0.5)  # Move y-axis label to the right
        self.ax0_r.set_ylim(self.y_axis_phtCount_min, self.y_axis_phtCount_max)
        style_axis(self.ax0_r)
        self.phtCount_lagoon = style_line(self.ax0_r, "phtCount", "red", style="-", opacity=0.9)

        # Second subplot: Temperature, Flow Rate
        self.ax1.set_xticklabels([])    # remove the x-axis ticks and labels
        # Temperature on left y-axis
        self.ax1.set_ylabel("Temperature\n(°C)")
        self.ax1.yaxis.set_label_coords(-0.045, 0.5)  # Move y-axis label to the left
        self.ax1.set_ylim(self.y_axis_temp_min, self.y_axis_temp_max)
        style_axis(self.ax1)
        self.temp_bioReactor = style_line(self.ax1, "Temp", "orange", style=":", opacity=0.5)
        self.temp_lagoon = style_line(self.ax1, "Temp Lagoon", "yellow", style=":", opacity=0.5)
        # Flow Rate on right y-axis
        self.ax1_r = self.ax1.twinx()
        self.ax1_r.set_ylabel("Flow Rate\n(mL/min)")
        self.ax1_r.yaxis.set_label_coords(1.045, 0.5)  # Move y-axis label to the right
        self.ax1_r.set_ylim(self.y_axis_flowRate_min, self.y_axis_flowRate_max)
        style_axis(self.ax1_r)
        self.flowRate_pump1 = style_line(self.ax1_r, "Flow Rate", "green", "-", opacity=0.9)
        self.flowRate_pump2 = style_line(self.ax1_r, "Flow Rate Lagoon", "lime", "-", opacity=0.9)

        # Third subplot: scatter plot for the event when sample extraction takes a sample
        self.ax2.set_ylabel("SE\nEvent")
        self.ax2.yaxis.set_label_coords(-0.045, 0.5)  # Move y-axis label to the left
        self.ax2.set_yticks([])
        self.ax2.set_ylim(1,1)
        self.ax2.set_xticks(x_axis_ticks)
        style_axis(self.ax2)
        self.sample_extraction_events, = self.ax2.plot([], [], label="Sample Extraction", marker="o", linestyle="", color="magenta")

        # Remove Matplotlib's default horizontal data padding.
        self.ax0.margins(x=0)
        self.ax0_r.margins(x=0)
        self.ax1.margins(x=0)
        self.ax1_r.margins(x=0)
        self.ax2.margins(x=0)

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
        self.ax0.set_position([0.07, 0.58, 0.860, 0.33])
        self.ax1.set_position([0.07, 0.20, 0.860, 0.33])
        self.ax2.set_position([0.07, 0.07, 0.860, 0.08])


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
        y_axis_od_min = QLabel(f"Y-axis OD Min:")
        y_axis_od_min.setStyleSheet(text_style)
        self.y_axis_od_min_edit = QLineEdit(str(self.y_axis_od_min))
        self.y_axis_od_min_edit.setStyleSheet(edit_style)
        y_axis_od_max = QLabel(f"Y-axis OD Max:")
        y_axis_od_max.setStyleSheet(text_style)
        self.y_axis_od_max_edit = QLineEdit(str(self.y_axis_od_max))
        self.y_axis_od_max_edit.setStyleSheet(edit_style)
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
        y_axis_flowRate_min = QLabel(f"Y-axis Flow Rate Min:")
        y_axis_flowRate_min.setStyleSheet(text_style)
        self.y_axis_flowRate_min_edit = QLineEdit(str(self.y_axis_flowRate_min))
        self.y_axis_flowRate_min_edit.setStyleSheet(edit_style)
        y_axis_flowRate_max = QLabel(f"Y-axis Flow Rate Max:")
        y_axis_flowRate_max.setStyleSheet(text_style)
        self.y_axis_flowRate_max_edit = QLineEdit(str(self.y_axis_flowRate_max))
        self.y_axis_flowRate_max_edit.setStyleSheet(edit_style)

        configuration_first_row_layout.addWidget(timespan)
        configuration_first_row_layout.addWidget(self.timespan_edit)
        configuration_first_row_layout.addWidget(sampling_time)
        configuration_first_row_layout.addWidget(self.sampling_time_edit)
        configuration_second_row_layout.addWidget(y_axis_od_min)
        configuration_second_row_layout.addWidget(self.y_axis_od_min_edit)
        configuration_second_row_layout.addWidget(y_axis_od_max)
        configuration_second_row_layout.addWidget(self.y_axis_od_max_edit)
        configuration_third_row_layout.addWidget(y_axis_phtCount_min)
        configuration_third_row_layout.addWidget(self.y_axis_phtCount_min_edit)
        configuration_third_row_layout.addWidget(y_axis_phtCount_max)
        configuration_third_row_layout.addWidget(self.y_axis_phtCount_max_edit)
        configuration_forth_row_layout.addWidget(y_axis_temp_min)
        configuration_forth_row_layout.addWidget(self.y_axis_temp_min_edit)
        configuration_forth_row_layout.addWidget(y_axis_temp_max)
        configuration_forth_row_layout.addWidget(self.y_axis_temp_max_edit)
        configuration_fifth_row_layout.addWidget(y_axis_flowRate_min)
        configuration_fifth_row_layout.addWidget(self.y_axis_flowRate_min_edit)
        configuration_fifth_row_layout.addWidget(y_axis_flowRate_max)
        configuration_fifth_row_layout.addWidget(self.y_axis_flowRate_max_edit)

        configuration_layout.addLayout(configuration_first_row_layout)
        configuration_layout.addLayout(configuration_second_row_layout)
        configuration_layout.addLayout(configuration_third_row_layout)
        configuration_layout.addLayout(configuration_forth_row_layout)
        configuration_layout.addLayout(configuration_fifth_row_layout)

        self.update_config_button = QPushButton("Update Configuration")
        self.update_config_button.setStyleSheet(button_style)
        self.update_config_button.setMaximumHeight(50)
        self.update_config_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        configuration_layout.addWidget(self.update_config_button)
        configuration_layout.addStretch()  # Push the button to the top
        
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
        self.log_name_edit = QLineEdit("")
        self.log_name_edit.setStyleSheet(edit_style)
        self.browse_location_button = QPushButton("Browse")
        self.browse_location_button.setStyleSheet(button_style)
        self.browse_location_button.setMaximumWidth(60)
        log_location = QLabel("Log Location:")
        log_location.setStyleSheet(text_style)
        self.log_location_label = QLabel("")
        self.log_location_label.setStyleSheet(text_style)
        self.start_logging_button = QPushButton("Start Logging")
        self.start_logging_button.setStyleSheet(button_style)
        self.start_logging_button.setMaximumHeight(40)
        self.start_logging_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.stop_logging_button = QPushButton("Stop Logging")
        self.stop_logging_button.setStyleSheet(button_style)
        self.stop_logging_button.setMaximumHeight(40)
        self.stop_logging_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.open_log_button = QPushButton("Open Logged Data")
        self.open_log_button.setStyleSheet(button_style)
        self.open_log_button.setMaximumHeight(40)
        self.open_log_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)


        data_logging_first_row_layout.addWidget(log_name)
        data_logging_first_row_layout.addWidget(self.log_name_edit)
        data_logging_second_row_layout.addWidget(log_location)
        data_logging_second_row_layout.addWidget(self.log_location_label)
        data_logging_second_row_layout.addWidget(self.browse_location_button)
        data_logging_third_row_layout.addWidget(self.start_logging_button)
        data_logging_third_row_layout.addWidget(self.stop_logging_button)
        data_logging_forth_row_layout.addWidget(self.open_log_button)

        data_logging_layout.addLayout(data_logging_first_row_layout)
        data_logging_layout.addLayout(data_logging_second_row_layout)
        data_logging_layout.addLayout(data_logging_third_row_layout)
        data_logging_layout.addLayout(data_logging_forth_row_layout)
        data_logging_layout.addStretch()  # Push the buttons to the top

        # Add groups to control panel layout
        control_panel_layout.addWidget(configuration_group)
        control_panel_layout.addWidget(data_logging_group)
        control_panel_section_widget.setLayout(control_panel_layout)

        # Main widget split: plot area takes ~3/4 width, control panel ~1/4.
        layout = QHBoxLayout(self)
        layout.addWidget(self.plot_section_widget, stretch=3)
        layout.addWidget(control_panel_section_widget, stretch=1)

    def read_settings_file(self):
        """Load plotting defaults from config/settings.ini."""
        config_path = resource_path("config/settings.ini")
        config = configparser.ConfigParser()
        config.read(str(config_path))
        return config

    def _sync_scrollbar_to_ax2(self):
        """Match the scrollbar width and horizontal offset to ax2's plotting area."""
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
        """Plot some test data to verify the plotting functionality."""
        import numpy as np
        x_data = np.arange(0, self.timespan_minutes * 60 + 1, self.sampling_time_seconds)
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
    




