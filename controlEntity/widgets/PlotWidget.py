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
from PySide6.QtWidgets import QApplication, QHBoxLayout, QMainWindow, QMessageBox, QScrollBar, QWidget, QVBoxLayout, QLCDNumber, QLineEdit, QComboBox, QCalendarWidget, QTextEdit, QTimeEdit
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

    def setup_ui(self):
        """Build the plotting canvas (3 stacked subplots with additional horizontal scrollbar at the bottom) and control panel, using settings.ini defaults"""
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

        button_style = """QPushButton {
                            background-color: LightBlue;
                            color: black;
                            border: 1px solid #5aa9c9;
                            border-radius: 4px; }
                            QPushButton:hover {
                                background-color: #9fdfff; }
                            QPushButton:pressed {
                                background-color: LightSkyBlue; }
                            QPushButton:disabled {
                                background-color: #d9d9d9;
                                color: #888888; } 
                            """

        groupbox_style = """QGroupBox {
                            font-weight: bold;
                            font-size: 14px;
                            color: #000000;
                            border: 2px solid '#000000';
                            border-radius: 10px;
                            margin-top: 10px;
                            background-color: 'darkgray';
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
                        color: black;
                        }"""

        # ===============================
        # Plot section
        # ===============================
        self.plot_section_widget = QWidget(self)

        self.fig, (self.ax0, self.ax1, self.ax2) = plt.subplots(3, 1)
        self.fig.suptitle("EvoFlow Data Visualization", color="black", fontweight="bold")

        x_axis_ticks = [i for i in range(0, self.timespan_minutes * 60 + 1, self.sampling_time_seconds)]

        # First subplot: OD, phtCount
        self.ax0.set_xticklabels([])    # remove the x-axis ticks and labels
        # OD on left y-axis
        self.ax0.set_ylabel("Optical Density\n(OD)")
        self.ax0.yaxis.set_label_coords(-0.045, 0.5)  # Move y-axis label to the left
        self.ax0.set_ylim(self.y_axis_od_min, self.y_axis_od_max)
        self.od_bioReactor, = self.ax0.plot([], [], label="OD", color="blue")
        self.od_lagoon, = self.ax0.plot([], [], label="OD Lagoon", color="cyan")
        # phtCount on right y-axis
        self.ax0_r = self.ax0.twinx()
        self.ax0_r.set_ylabel("Photon Count\n(MHz)")
        self.ax0_r.yaxis.set_label_coords(1.045, 0.5)  # Move y-axis label to the right
        self.ax0_r.set_ylim(self.y_axis_phtCount_min, self.y_axis_phtCount_max)
        self.phtCount_lagoon, = self.ax0_r.plot([], [], label="phtCount", color="red")

        # Second subplot: Temperature, Flow Rate
        self.ax1.set_xticklabels([])    # remove the x-axis ticks and labels
        # Temperature on left y-axis
        self.ax1.set_ylabel("Temperature\n(°C)")
        self.ax1.yaxis.set_label_coords(-0.045, 0.5)  # Move y-axis label to the left
        self.ax1.set_ylim(self.y_axis_temp_min, self.y_axis_temp_max)
        self.temp_bioReactor, = self.ax1.plot([], [], label="Temp", color="orange")
        self.temp_lagoon, = self.ax1.plot([], [], label="Temp Lagoon", color="yellow")
        # Flow Rate on right y-axis
        self.ax1_r = self.ax1.twinx()
        self.ax1_r.set_ylabel("Flow Rate\n(mL/min)")
        self.ax1_r.yaxis.set_label_coords(1.045, 0.5)  # Move y-axis label to the right
        self.ax1_r.set_ylim(self.y_axis_flowRate_min, self.y_axis_flowRate_max)
        self.flowRate_pump1, = self.ax1_r.plot([], [], label="Flow Rate", color="green")
        self.flowRate_pump2, = self.ax1_r.plot([], [], label="Flow Rate Lagoon", color="lime")

        # Third subplot: scatter plot for the event when sample extraction takes a sample
        self.ax2.set_ylabel("SE\nEvent")
        self.ax2.yaxis.set_label_coords(-0.045, 0.5)  # Move y-axis label to the left
        self.ax2.set_yticks([0, 1])
        self.ax2.set_xticks(x_axis_ticks)
        self.sample_extraction_events, = self.ax2.plot([], [], label="Sample Extraction", marker="o", linestyle="", color="magenta")

        # Adjust layout and create canvas
        self.fig.tight_layout(rect=[0, 0.03, 1, 0.95])  # leave space for the suptitle
        self.fig.set_facecolor('#fff6d4')
        self.canvas = FigureCanvas(self.fig)
        self.ax0.set_position([0.07, 0.58, 0.860, 0.33])
        self.ax1.set_position([0.07, 0.20, 0.860, 0.33])
        self.ax2.set_position([0.07, 0.07, 0.860, 0.08])


        # Scrollbar for x-axis (time)
        self.scrollbar_ax = QScrollBar(Qt.Horizontal, self)
        self.scrollbar_ax.setMinimumHeight(20)
        self.scrollbar_ax.setMinimum(0)
        self.scrollbar_ax.setMaximum(self.timespan_minutes * 60)
        self.scrollbar_ax.setPageStep(self.sampling_time_seconds)
        self.scrollbar_ax.setSingleStep(self.sampling_time_seconds)
        self.scrollbar_ax.setValue(self.timespan_minutes * 60)  # Start at the end of the timespan

        self.scrollbar_row_widget = QWidget(self.plot_section_widget)
        self.scrollbar_row_layout = QHBoxLayout(self.scrollbar_row_widget)
        self.scrollbar_row_layout.setContentsMargins(0, 0, 0, 0)
        self.scrollbar_row_layout.setSpacing(0)
        self.scrollbar_row_layout.addWidget(self.scrollbar_ax)


        self.plot_section_widget_layout = QVBoxLayout(self.plot_section_widget)
        self.plot_section_widget_layout.addWidget(self.canvas)
        self.plot_section_widget_layout.addWidget(self.scrollbar_row_widget)

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
        configuration_layout.addWidget(self.update_config_button)
        
        
        data_logging_group = QGroupBox("Data Logging")
        data_logging_group.setStyleSheet(groupbox_style)
        data_logging_layout = QVBoxLayout(data_logging_group)

        



        control_panel_layout.addWidget(configuration_group)
        control_panel_layout.addWidget(data_logging_group)
        control_panel_section_widget.setLayout(control_panel_layout)






        # Layout
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

        left_px = max(0, int(ax2_pos.x0 * canvas_width))
        width_px = max(1, int(ax2_pos.width * canvas_width))
        right_px = max(0, canvas_width - (left_px + width_px))

        self.scrollbar_ax.setFixedWidth(width_px)
        self.scrollbar_row_layout.setContentsMargins(left_px, 0, right_px, 0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QTimer.singleShot(0, self._sync_scrollbar_to_ax2)
    




