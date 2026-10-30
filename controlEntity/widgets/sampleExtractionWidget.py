"""
Sample Extraction Widget for graphical representation of the sample extraction process

Project: EvoFlow Innosuisse
Author: Patipol Thanuphol, Scientific Researcher at ZHAW — thau@zhaw.ch | patipol.thanuphol@zhaw.ch
Created: April 2026
"""

import time
import os
import configparser
from PySide6.QtWidgets import QApplication, QHBoxLayout, QMainWindow, QMessageBox, QWidget, QVBoxLayout, QLCDNumber, QLineEdit, QComboBox, QCalendarWidget, QTextEdit, QTimeEdit
from PySide6.QtWidgets import QPushButton, QGroupBox, QTabWidget, QTableView, QMenuBar, QStatusBar, QLabel, QCheckBox, QColorDialog
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import Qt, QFile, QTimer, QDate, QTime, QIODeviceBase, QEvent, Signal, Slot, QObject
from PySide6.QtGui import QColor, QKeyEvent, QPainter, QTextCharFormat, QStandardItemModel, QStandardItem, QWheelEvent, QCloseEvent, QAction, QPixmap

from controlEntity.utils import resource_path, Utils
from evoflow.device.sample_extraction import SampleExtractionTelemetry
from controlEntity.widgets.customizedImageButton import CustomizedImageButton


class RackSelectionWidget(QWidget):
    """Transparent 12x8 rack overlay with hover and single-cell selection"""
    # ================================
    # Signals required for widget
    # ================================

    rack_position_selected = Signal(tuple)

    def __init__(self, parent=None, rows: int = 8, cols: int = 12, cell_size: int = 20):
        super().__init__(parent)
        self.rows = rows
        self.cols = cols
        self.cell_size = cell_size
        self.hover_position = None
        self.selected_position = None
        self.filled_position : list = []

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        self.setFixedSize(self.cols * self.cell_size, self.rows * self.cell_size)

        self.hover_color = QColor(255, 165, 0, 130) # light orange with transparency
        self.selected_color = QColor(255, 100, 0, 190)    # darker orange with more opacity
        self.grid_color = QColor(255, 255, 255, 0) # 100% transparent

    def _position_from_point(self, pos):
        col = pos.x() // self.cell_size
        row = pos.y() // self.cell_size
        if 0 <= row < self.rows and 0 <= col < self.cols:
            return (row, col)
        return None

    def mouseMoveEvent(self, event):
        new_hover = self._position_from_point(event.position().toPoint())
        if new_hover != self.hover_position:
            self.hover_position = new_hover
            self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        if self.hover_position is not None:
            self.hover_position = None
            self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            selected = self._position_from_point(event.position().toPoint())
            if selected is not None:
                self.selected_position = selected
                self.rack_position_selected.emit(selected)
                self.update()
        super().mousePressEvent(event)

    def clear_selection(self):
        self.selected_position = None
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        if self.hover_position is not None:
            row, col = self.hover_position
            painter.fillRect(
                col * self.cell_size,
                row * self.cell_size,
                self.cell_size,
                self.cell_size,
                self.hover_color,
            )

        if self.filled_position is not None:
            for pos in self.filled_position:
                row, col = pos
                painter.fillRect(
                    col * self.cell_size,
                    row * self.cell_size,
                    self.cell_size,
                    self.cell_size,
                    QColor(0, 255, 0, 150),  # green with transparency
                )

        if self.selected_position is not None:
            row, col = self.selected_position
            painter.fillRect(
                col * self.cell_size,
                row * self.cell_size,
                self.cell_size,
                self.cell_size,
                self.selected_color,
            )

        painter.setPen(self.grid_color)
        for row in range(self.rows + 1):
            y = row * self.cell_size
            painter.drawLine(0, y, self.cols * self.cell_size, y)
        for col in range(self.cols + 1):
            x = col * self.cell_size
            painter.drawLine(x, 0, x, self.rows * self.cell_size)

        super().paintEvent(event)

    @Slot(tuple)
    def mark_filled_position(self, position: tuple):
        """Mark positions in therack that have been filled with samples"""
        if position not in self.filled_position:
            self.filled_position.append(position)
            self.update()

    @Slot(bool)
    def reset_filled_positions(self):
        """Reset all filled positions to default state"""
        self.filled_position.clear()
        self.update()


class SampleExtractionWidget(QWidget):
    """SampleExtractionWidget for graphical representation of the SampleExtraction system"""
    # ================================
    # Signals required for widget
    # ================================

    # Outgoing signals to request actions in the worker
    start_manual_sample_extraction_requested = Signal(tuple)
    start_auto_sample_extraction_requested = Signal(bool)
    stop_auto_sample_extraction_requested = Signal(bool)
    auto_mode_start_position_changed = Signal(tuple)
    auto_mode_sampling_interval_changed = Signal(int)
    auto_mode_volume_per_sample_changed = Signal(int)
    sample_extraction_auto_mode_changed = Signal(bool)

    def __init__(self, width: int=560, height: int=195):
        """"Initialize the SampleExtractionWidget"""
        super().__init__()
        self._width: int = width
        self._height: int = height
        self.widget_selected_position = None
        self.setup_ui()
        self.connect_signals()
        self.sample_extraction_auto_mode : bool = False
        # self.load_default_config()
        self.utils = Utils()

    def setup_ui(self):
        """Set up the UI components"""
        self.setFixedSize(self._width, self._height)

        self.selected_label = QLabel("Selected Position:", self)
        self.selected_label.setGeometry(5, 28, 300, 20)
        self.selected_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.selected_label.setStyleSheet("color: lightblue; font-weight: bold;")

        button_style = """QPushButton {
                            background-color: LightBlue;
                            color: black;
                            border: 1px solid #5aa9c9;
                            border-radius: 4px; }
                            QPushButton:hover {
                                background-color: #5dc9ff; }
                            QPushButton:pressed {
                                background-color: #007cba; }
                            QPushButton:disabled {
                                background-color: #d9d9d9;
                                color: #888888; } 
                            """
        # Component signals (dynamic values that can change during runtime)
        self.edit_style = """QLineEdit {
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
                            background-color: #333333;
                            color: #888888; }
                        """
        
        # Info Labels (Static fonts, this won't change)
        font_component = """font-weight: bold; color: Orange; font-size: 11px;"""
        font_description = """font-weight: bold; color: LightGreen; font-size: 11px;"""
        font_value = """font-weight: bold; font-size: 16px; color: #575757;"""
        font_value_2 = """font-weight: bold; font-size: 16px; color: #0070a3;"""
        font_small_value = """color: White; font-size: 11px;"""

        info_x_axis_motor_temp = QLabel("X-Axis Temp:", self)
        info_x_axis_motor_temp.setStyleSheet(font_component)
        info_x_axis_motor_temp.setGeometry(8, 5, 90, 20)
        info_y_axis_motor_temp = QLabel("Y-Axis Temp:", self)
        info_y_axis_motor_temp.setStyleSheet(font_component)
        info_y_axis_motor_temp.setGeometry(138, 5, 90, 20)
        info_z_axis_motor_temp = QLabel("Z-Axis Temp:", self)
        info_z_axis_motor_temp.setStyleSheet(font_component)
        info_z_axis_motor_temp.setGeometry(268, 5, 90, 20)
        info_ambient_temp = QLabel("Ambient Temp:", self)
        info_ambient_temp.setStyleSheet(font_component)
        info_ambient_temp.setGeometry(398, 5, 90, 20)

        self.x_axis_motor_temp_label = QLabel("0.0 °C", self)
        self.x_axis_motor_temp_label.setStyleSheet(font_small_value)
        self.x_axis_motor_temp_label.setGeometry(88, 5, 90, 20)
        self.y_axis_motor_temp_label = QLabel("0.0 °C", self)
        self.y_axis_motor_temp_label.setStyleSheet(font_small_value)    
        self.y_axis_motor_temp_label.setGeometry(218, 5, 90, 20)
        self.z_axis_motor_temp_label = QLabel("0.0 °C", self)
        self.z_axis_motor_temp_label.setStyleSheet(font_small_value)
        self.z_axis_motor_temp_label.setGeometry(348, 5, 90, 20)
        self.ambient_temp_label = QLabel("0.0 °C", self)
        self.ambient_temp_label.setStyleSheet(font_small_value)
        self.ambient_temp_label.setGeometry(490, 5, 90, 20)

        self.sample_extraction_start_manual_button = QPushButton("Start", self)
        self.sample_extraction_start_manual_button.setGeometry(8, 185, 184, 35)
        self.sample_extraction_start_manual_button.setStyleSheet(button_style)
        self.sample_extraction_start_manual_button.setVisible(True)
        self.sample_extraction_start_auto_button = QPushButton("Start", self)
        self.sample_extraction_start_auto_button.setGeometry(8, 185, 90, 35)
        self.sample_extraction_start_auto_button.setStyleSheet(button_style)
        self.sample_extraction_start_auto_button.setVisible(False)
        self.sample_extraction_stop_auto_button = QPushButton("Stop", self)
        self.sample_extraction_stop_auto_button.setGeometry(102, 185, 90, 35)
        self.sample_extraction_stop_auto_button.setStyleSheet(button_style)
        self.sample_extraction_stop_auto_button.setVisible(False)
        self.sample_extraction_waste_pos_button = QPushButton("Waste", self)
        self.sample_extraction_waste_pos_button.setGeometry(220, 91, 52, 36)
        self.sample_extraction_waste_pos_button.setStyleSheet(button_style)
        self.sample_extraction_change_bottle_button = QPushButton("Change Waste", self)
        self.sample_extraction_change_bottle_button.setGeometry(200, 150, 90, 20)
        self.sample_extraction_change_bottle_button.setStyleSheet(button_style)
        self.sample_extraction_change_tray_button = QPushButton("Change Tray", self)
        self.sample_extraction_change_tray_button.setGeometry(200, 175, 90, 20)
        self.sample_extraction_change_tray_button.setStyleSheet(button_style)
        self.homing_button = QPushButton("Homing", self)
        self.homing_button.setGeometry(200, 200, 90, 20)
        self.homing_button.setStyleSheet(button_style)
        self.reset_filled_tray_btn = QPushButton("Reset Filled\nTray", self)
        self.reset_filled_tray_btn.setGeometry(116, 52, 80, 35)
        self.reset_filled_tray_btn.setStyleSheet(button_style)

        self.auto_manual_customized_btn = CustomizedImageButton(110, 40, False, "Manual.png", "Auto.png", "Auto_Man_pressed.png", self)
        self.auto_manual_customized_btn.move(5, 50)

        info_start_position = QLabel("Start Pos.:", self)
        info_start_position.setGeometry(8, 100, 60, 20)
        info_start_position.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        info_start_position.setStyleSheet(font_component)
        info_sampling_interval = QLabel("Sampling Interval:", self)
        info_sampling_interval.setGeometry(8, 130, 105, 20)
        info_sampling_interval.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        info_sampling_interval.setStyleSheet(font_component)
        info_volume_per_sample = QLabel("Volume/Sample:", self)
        info_volume_per_sample.setGeometry(8, 160, 105, 20)
        info_volume_per_sample.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        info_volume_per_sample.setStyleSheet(font_component)

        self.start_position_edit = QLineEdit(self)
        self.start_position_edit.setGeometry(112, 100, 80, 20)
        self.start_position_edit.setStyleSheet(self.edit_style)
        self.start_position_edit.setEnabled(False)
        self.sampling_interval_edit = QLineEdit(self)
        self.sampling_interval_edit.setGeometry(112, 130, 80, 20)
        self.sampling_interval_edit.setStyleSheet(self.edit_style)
        self.sampling_interval_edit.setEnabled(False)
        self.volume_per_sample_edit = QLineEdit(self)
        self.volume_per_sample_edit.setGeometry(112, 160, 80, 20)
        self.volume_per_sample_edit.setStyleSheet(self.edit_style)
        self.volume_per_sample_edit.setEnabled(False)   

        self.sample_extraction_rack = RackSelectionWidget(self, rows=8, cols=12, cell_size=20)
        self.sample_extraction_rack.move(295, 42)

    def connect_signals(self):
        """Connect signals to their respective slots"""
        self.sample_extraction_start_manual_button.clicked.connect(self._on_start_manual_clicked)
        self.sample_extraction_start_auto_button.clicked.connect(self._on_start_auto_clicked)
        self.sample_extraction_stop_auto_button.clicked.connect(self._on_stop_auto_clicked)
        self.sample_extraction_change_bottle_button.clicked.connect(self._on_change_bottle_clicked)
        self.sample_extraction_change_tray_button.clicked.connect(self._on_change_tray_clicked)
        self.sample_extraction_waste_pos_button.clicked.connect(self._on_waste_pos_clicked)
        self.homing_button.clicked.connect(self._on_homing_clicked)
        self.auto_manual_customized_btn.clicked.connect(self.handle_sample_extraction_auto_manual_mode_toggle)
        self.sample_extraction_rack.rack_position_selected.connect(self._on_rack_position_selected)
        self.reset_filled_tray_btn.clicked.connect(self.sample_extraction_rack.reset_filled_positions)

    def _on_rack_position_selected(self, position):
        """Track the latest selected rack position in (row, col)"""
        self.widget_selected_position = position
        self.selected_label.setText(f"Selected Position: Row {position[0]}, Col {position[1]}")
    
    def _on_start_manual_clicked(self):
        self.start_manual_sample_extraction_requested.emit(self.widget_selected_position)

    def _on_start_auto_clicked(self):
        position = self.start_position_edit.text().strip()
        ret_position = self.utils.return_row_col_sample_extraction(position)
        try:
            self.auto_mode_start_position_changed.emit(ret_position)
            self.auto_mode_sampling_interval_changed.emit(int(self.sampling_interval_edit.text().strip()))
            self.auto_mode_volume_per_sample_changed.emit(int(self.volume_per_sample_edit.text().strip()))
            self.start_auto_sample_extraction_requested.emit(True)
        except ValueError:
            if ret_position is None:
                QMessageBox.warning(self, "Invalid Start Position", "Please enter a valid start position (e.g., A1, B2, etc.).")
            else:
                QMessageBox.warning(self, "Invalid Sampling Interval", "Please enter a valid integer for the sampling interval.")

    def _on_stop_auto_clicked(self):
        self.stop_auto_sample_extraction_requested.emit(True)
        self.auto_manual_customized_btn.change_icon_paths("Manual.png", "Auto.png", "Auto_Man_pressed.png")

    def _on_change_bottle_clicked(self):
        """Handle Change Bottle button click"""
        self.sample_extraction_rack.clear_selection()
        self.widget_selected_position = [253, 253]
        self.selected_label.setText(f"Selected Position: Row {self.widget_selected_position[0]}, Col {self.widget_selected_position[1]}")

    def _on_change_tray_clicked(self):
        """Handle Change Tray button click"""
        self.sample_extraction_rack.clear_selection()
        self.widget_selected_position = [254, 254]
        self.selected_label.setText(f"Selected Position: Row {self.widget_selected_position[0]}, Col {self.widget_selected_position[1]}")

    def _on_waste_pos_clicked(self):
        """Handle Waste Position button click"""
        self.sample_extraction_rack.clear_selection()
        self.widget_selected_position = [255, 255]
        self.selected_label.setText(f"Selected Position: Row {self.widget_selected_position[0]}, Col {self.widget_selected_position[1]}")

    def _on_homing_clicked(self):
        """Handle Homing button click"""
        self.sample_extraction_rack.clear_selection()
        self.widget_selected_position = [252, 252]
        self.selected_label.setText(f"Selected Position: Row {self.widget_selected_position[0]}, Col {self.widget_selected_position[1]}")

    def handle_sample_extraction_auto_manual_mode_toggle(self):
        """Handle the toggle between auto and manual modes"""
        self.sample_extraction_auto_mode = self.auto_manual_customized_btn.isChecked()
        if self.sample_extraction_auto_mode:
            self.sample_extraction_start_manual_button.setVisible(False)
            self.sample_extraction_start_auto_button.setVisible(True)
            self.sample_extraction_stop_auto_button.setVisible(True)
            self.start_position_edit.setEnabled(True)
            self.sampling_interval_edit.setEnabled(True)
            self.volume_per_sample_edit.setEnabled(True)
        else:
            self.sample_extraction_start_manual_button.setVisible(True)
            self.sample_extraction_start_auto_button.setVisible(False)
            self.sample_extraction_stop_auto_button.setVisible(False)
            self.start_position_edit.setEnabled(False)
            self.sampling_interval_edit.setEnabled(False)
            self.volume_per_sample_edit.setEnabled(False)
        self.sample_extraction_auto_mode_changed.emit(self.sample_extraction_auto_mode)      

    @Slot(SampleExtractionTelemetry)
    def update_telemetry_sample_extraction(self, telemetry):
        self.x_axis_motor_temp_label.setText(f"{telemetry.x_axis_motor_temp:.1f} °C")
        self.y_axis_motor_temp_label.setText(f"{telemetry.y_axis_motor_temp:.1f} °C")
        self.z_axis_motor_temp_label.setText(f"{telemetry.z_axis_motor_temp:.1f} °C")
        self.ambient_temp_label.setText(f"{telemetry.ambient_temp:.1f} °C")

    @Slot()
    def handle_blink_timer_timeout(self):
        """Handle the blink timer timeout for the customized button"""
        if self.auto_manual_customized_btn.icon_path_checked == "Auto.png":
            self.auto_manual_customized_btn.change_icon_paths("Manual.png", "Auto_blink.png", "Auto_Man_pressed.png")
        else:
            self.auto_manual_customized_btn.change_icon_paths("Manual.png", "Auto.png", "Auto_Man_pressed.png")
            

    

