import time
import os
import configparser
from PySide6.QtWidgets import QApplication, QHBoxLayout, QMainWindow, QMessageBox, QWidget, QVBoxLayout, QLCDNumber, QLineEdit, QComboBox, QCalendarWidget, QTextEdit, QTimeEdit
from PySide6.QtWidgets import QPushButton, QGroupBox, QTabWidget, QTableView, QMenuBar, QStatusBar, QLabel, QCheckBox, QColorDialog
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import Qt, QFile, QTimer, QDate, QTime, QIODeviceBase, QEvent, Signal, Slot, QObject
from PySide6.QtGui import QColor, QKeyEvent, QPainter, QTextCharFormat, QStandardItemModel, QStandardItem, QWheelEvent, QCloseEvent, QAction, QPixmap

from controlEntity.utils import resource_path
from evoflow.device.sample_extraction import SampleExtractionTelemetry


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

class SampleExtractionWidget(QWidget):
    """SampleExtractionWidget for graphical representation of the SampleExtraction system"""
    # ================================
    # Signals required for widget
    # ================================

    # Outgoing signals to request actions in the worker
    start_sample_extraction_requested = Signal(tuple)
    test_read_position_requested = Signal()

    def __init__(self, width: int=560, height: int=195):
        """"Initialize the SampleExtractionWidget"""
        super().__init__()
        self._width: int = width
        self._height: int = height
        self.widget_selected_position = None
        self.setup_ui()
        self.connect_signals()
        # self.load_default_config()

    def setup_ui(self):
        """Set up the UI components"""
        self.setFixedSize(self._width, self._height)

        self.selected_label = QLabel("Selected Position:", self)
        self.selected_label.setGeometry(12, 3, 300, 20)
        self.selected_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.selected_label.setStyleSheet("color: lightblue; font-weight: bold;")

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
        self.sample_extraction_start_button = QPushButton("Start", self)
        self.sample_extraction_start_button.setGeometry(12, 168, 270, 20)
        self.sample_extraction_start_button.setStyleSheet(button_style)
        self.sample_extraction_change_bottle_button = QPushButton("Change Bottle", self)
        self.sample_extraction_change_bottle_button.setGeometry(12, 143, 85, 20)
        self.sample_extraction_change_bottle_button.setStyleSheet(button_style)
        self.sample_extraction_change_tray_button = QPushButton("Change Tray", self)
        self.sample_extraction_change_tray_button.setGeometry(105, 143, 85, 20)
        self.sample_extraction_change_tray_button.setStyleSheet(button_style)
        self.sample_extraction_waste_pos_button = QPushButton("Waste Position", self)
        self.sample_extraction_waste_pos_button.setGeometry(197, 143, 85, 20)
        self.sample_extraction_waste_pos_button.setStyleSheet(button_style)

        self.test_read_position_button = QPushButton("Test Get Position", self)
        self.test_read_position_button.setGeometry(105, 100, 85, 20)
        self.test_read_position_button.setStyleSheet(button_style)

        self.sample_extraction_rack = RackSelectionWidget(self, rows=8, cols=12, cell_size=20)
        self.sample_extraction_rack.move(295, 12)
        self.sample_extraction_rack.rack_position_selected.connect(self._on_rack_position_selected)

    def connect_signals(self):
        """Connect signals to their respective slots"""
        self.sample_extraction_start_button.clicked.connect(self._on_start_clicked)
        self.sample_extraction_change_bottle_button.clicked.connect(self._on_change_bottle_clicked)
        self.sample_extraction_change_tray_button.clicked.connect(self._on_change_tray_clicked)
        self.sample_extraction_waste_pos_button.clicked.connect(self._on_waste_pos_clicked)

        self.test_read_position_button.clicked.connect(self._on_test_read_position_clicked)

    def _on_rack_position_selected(self, position):
        """Track the latest selected rack position in (row, col)"""
        self.widget_selected_position = position
        self.selected_label.setText(f"Selected Position: Row {position[0]}, Col {position[1]}")
    
    def _on_start_clicked(self):
        self.start_sample_extraction_requested.emit(self.widget_selected_position)

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

    def _on_test_read_position_clicked(self):
        """Handle Test Get Position button click"""
        self.test_read_position_requested.emit()

    @Slot(SampleExtractionTelemetry)
    def update_telemetry(self, telemetry):
        print(f"Updating Sample Extraction Widget telemetry: Row {telemetry.position[0]}, Col {telemetry.position[1]}")
        print(f"done_flag: {telemetry.done_flag}")
        self.selected_label.setText(f"Selected Position: Row {telemetry.position[0]}, Col {telemetry.position[1]}")
