import time
import os
import configparser
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox, QWidget, QVBoxLayout, QLCDNumber, QLineEdit, QComboBox, QCalendarWidget, QTextEdit, QTimeEdit
from PySide6.QtWidgets import QPushButton, QGroupBox, QTabWidget, QTableView, QMenuBar, QStatusBar, QLabel, QCheckBox, QColorDialog
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import Qt, QFile, QTimer, QDate, QTime, QIODeviceBase, QEvent, Signal, Slot, QObject
from PySide6.QtGui import QKeyEvent, QTextCharFormat, QStandardItemModel, QStandardItem, QWheelEvent, QCloseEvent, QAction, QPixmap

from controlEntity.widgets.TapSwitchWidget import TapSwitch
from controlEntity.utils import resource_path
from evoflow.device.evoflow import EvoFlowTelemetry


class EvoFlowWidget(QWidget):
    """EvoFlowWidget for graphical representation of the EvoFlow system"""
    # ================================
    # Signals required for widget
    # ================================
    
    # Outgoing signals (to request actions, handle for all components of the same type as the protocol is designed that way)
    pump_on_off_requested = Signal(bool, bool, bool, bool)
    magneticStirrer_on_off_requested = Signal(bool, bool)
    od_on_off_requested = Signal(bool, bool)
    tempCtrl_on_off_requested = Signal(bool, bool)
    valve_on_off_requested = Signal(bool, bool)
    phtCount_on_off_requested = Signal(bool)

    pump_sp_changed = Signal(float, float, float, float)
    magneticStirrer_sp_changed = Signal(float, float)
    tempCtrl_sp_changed = Signal(float, float)

    # Incoming signals (to update the widget)
    evoflow_telemetry_updated = Signal(EvoFlowTelemetry)

    def __init__(self, width: int=1800, height: int=450):
        """"Initialize the EvoFlowWidget"""
        super().__init__()
        self._width: int = width
        self._height: int = height
        self.setup_ui()
        self.connect_signals()
        self.load_default_config()

    def setup_ui(self):
        """Set up the UI components"""
        self.setFixedSize(self._width, self._height)

        # Background
        self.background = QLabel(self)
        self.background.setFixedSize(self._width, self._height)
        self.background.setGeometry(0, 0, self._width, self._height)
        background_img = QPixmap(os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "EvoFlow_GUI_Diagram_long.png"))
        scaled_background = background_img.scaled(self._width, self._height, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.background.setPixmap(scaled_background)


        # Info Labels (Static fonts, this won't change)
        font_component = """font-weight: bold; color: Orange;"""
        font_description = """font-weight: bold; color: LightGreen;"""
        font_value = """font-weight: bold; font-size: 18px; color: #575757;"""
        font_value_2 = """font-weight: bold; font-size: 18px; color: #0070a3;"""
        font_small_value = """color: White;"""

        info_pump_1 = QLabel("Pump 1", self)
        info_pump_1.setGeometry(90, 283, 50, 20)
        info_pump_1.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        info_pump_1.setStyleSheet(font_component)
        info_pump_1_sp = QLabel("SP(rpm):", self)
        info_pump_1_sp.setGeometry(15, 300, 100, 20)
        info_pump_1_sp.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        info_pump_1_sp.setStyleSheet(font_small_value)

        info_pump_2 = QLabel("Pump 2", self)
        info_pump_2.setGeometry(650, 283, 50, 20)
        info_pump_2.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        info_pump_2.setStyleSheet(font_component)
        info_pump_2_sp = QLabel("SP(rpm):", self)
        info_pump_2_sp.setGeometry(575, 300, 100, 20)
        info_pump_2_sp.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        info_pump_2_sp.setStyleSheet(font_small_value)

        info_pump_3 = QLabel("Pump 3", self)
        info_pump_3.setGeometry(1123, 304, 50, 20)
        info_pump_3.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        info_pump_3.setStyleSheet(font_component)
        info_pump_3_sp = QLabel("SP(rpm):", self)
        info_pump_3_sp.setGeometry(1048, 321, 100, 20)
        info_pump_3_sp.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        info_pump_3_sp.setStyleSheet(font_small_value)

        info_pump_4 = QLabel("Pump 4", self)
        info_pump_4.setGeometry(1123, 138, 50, 20)
        info_pump_4.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        info_pump_4.setStyleSheet(font_component)
        info_pump_4_sp = QLabel("SP(rpm):", self)
        info_pump_4_sp.setGeometry(1048, 155, 100, 20)
        info_pump_4_sp.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        info_pump_4_sp.setStyleSheet(font_small_value)

        info_magneticStirrer_bioreactor = QLabel("Magnetic Stirrer", self)
        info_magneticStirrer_bioreactor.setGeometry(239, 305, 100, 20)
        info_magneticStirrer_bioreactor.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        info_magneticStirrer_bioreactor.setStyleSheet(font_component)
        info_sp_magneticStirrer_bioreactor = QLabel("SP(rpm):", self)
        info_sp_magneticStirrer_bioreactor.setGeometry(187, 325, 100, 20)
        info_sp_magneticStirrer_bioreactor.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        info_sp_magneticStirrer_bioreactor.setStyleSheet(font_small_value)

        info_magneticStirrer_lagoon = QLabel("Magnetic Stirrer", self)
        info_magneticStirrer_lagoon.setGeometry(766, 305, 100, 20)
        info_magneticStirrer_lagoon.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        info_magneticStirrer_lagoon.setStyleSheet(font_component)
        info_sp_magneticStirrer_lagoon = QLabel("SP(rpm):", self)
        info_sp_magneticStirrer_lagoon.setGeometry(714, 325, 100, 20)
        info_sp_magneticStirrer_lagoon.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        info_sp_magneticStirrer_lagoon.setStyleSheet(font_small_value)

        info_od_bioreactor = QLabel("Optical\nDensity", self)
        info_od_bioreactor.setGeometry(160, 158, 100, 40)
        info_od_bioreactor.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        info_od_bioreactor.setStyleSheet(font_component)

        info_od_lagoon = QLabel("Optical\nDensity", self)
        info_od_lagoon.setGeometry(687, 158, 100, 40)
        info_od_lagoon.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        info_od_lagoon.setStyleSheet(font_component)

        info_tempCtrl_bioreactor = QLabel("Temp Ctrl", self)
        info_tempCtrl_bioreactor.setGeometry(349, 165, 100, 40)
        info_tempCtrl_bioreactor.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        info_tempCtrl_bioreactor.setStyleSheet(font_component)
        info_sp_tempCtrl_bioreactor = QLabel("SP(°C):", self)
        info_sp_tempCtrl_bioreactor.setGeometry(297, 195, 100, 20)
        info_sp_tempCtrl_bioreactor.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        info_sp_tempCtrl_bioreactor.setStyleSheet(font_small_value)

        info_tempCtrl_lagoon = QLabel("Temp Ctrl", self)
        info_tempCtrl_lagoon.setGeometry(876, 165, 100, 40)
        info_tempCtrl_lagoon.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        info_tempCtrl_lagoon.setStyleSheet(font_component)
        info_sp_tempCtrl_lagoon = QLabel("SP(°C):", self)
        info_sp_tempCtrl_lagoon.setGeometry(824, 195, 100, 20)
        info_sp_tempCtrl_lagoon.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        info_sp_tempCtrl_lagoon.setStyleSheet(font_small_value)

        info_phtCounter_lagoon = QLabel("Photon Counter", self)
        info_phtCounter_lagoon.setGeometry(876, 120, 100, 40)
        info_phtCounter_lagoon.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        info_phtCounter_lagoon.setStyleSheet(font_component)

        info_valve_bio2lag = QLabel("Valve\nBio2Lag", self)
        info_valve_bio2lag.setGeometry(490, 267, 100, 40)
        info_valve_bio2lag.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        info_valve_bio2lag.setStyleSheet(font_component)

        info_valve_sug2lag = QLabel("Valve\nSug2Lag", self)
        info_valve_sug2lag.setGeometry(518, 176, 100, 40)
        info_valve_sug2lag.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        info_valve_sug2lag.setStyleSheet(font_component)

        info_from_medium = QLabel("From Medium", self)
        info_from_medium.setGeometry(10, 210, 100, 20)
        info_from_medium.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        info_from_medium.setStyleSheet(font_description)

        info_to_waste = QLabel("To Waste", self)
        info_to_waste.setGeometry(1225, 247, 100, 20)
        info_to_waste.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        info_to_waste.setStyleSheet(font_description)

        info_to_waste_sample = QLabel("To Waste / Sample", self)
        info_to_waste_sample.setGeometry(1225, 80, 120, 20)
        info_to_waste_sample.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        info_to_waste_sample.setStyleSheet(font_description)

        info_overlight = QLabel("Overlight\nDetected", self)
        info_overlight.setGeometry(866, 70, 120, 40)
        info_overlight.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        info_overlight.setStyleSheet(font_component)

        info_bioreactor = QLabel("Bioreactor", self)
        info_bioreactor.setGeometry(188, 6, 200, 35)
        info_bioreactor.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        info_bioreactor.setStyleSheet("""font-weight: bold; font-size: 24px; color: white""")

        info_lagoon = QLabel("Lagoon", self)
        info_lagoon.setGeometry(715, 6, 200, 35)
        info_lagoon.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        info_lagoon.setStyleSheet("""font-weight: bold; font-size: 24px; color: white""")

        info_sugar = QLabel("Sugar", self)
        info_sugar.setGeometry(432, 45, 100, 25)
        info_sugar.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        info_sugar.setStyleSheet("""font-weight: bold; font-size: 18px; color: white""")

        info_waste = QLabel("Waste", self)
        info_waste.setGeometry(1315, 170, 100, 25)
        info_waste.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        info_waste.setStyleSheet("""font-weight: bold; font-size: 18px; color: black""")

        info_temp_bioreactor = QLabel("Temp:", self)
        info_temp_bioreactor.setGeometry(237, 153, 100, 25)
        info_temp_bioreactor.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        info_temp_bioreactor.setStyleSheet(font_value)

        info_od_bioreactor = QLabel("OD:", self)
        info_od_bioreactor.setGeometry(237, 203, 100, 25)
        info_od_bioreactor.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        info_od_bioreactor.setStyleSheet(font_value)

        info_phtCount_lagoon = QLabel("PHT Count:", self)
        info_phtCount_lagoon.setGeometry(764, 103, 100, 25)
        info_phtCount_lagoon.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        info_phtCount_lagoon.setStyleSheet(font_value)

        info_temp_lagoon = QLabel("Temp:", self)
        info_temp_lagoon.setGeometry(764, 153, 100, 25)
        info_temp_lagoon.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        info_temp_lagoon.setStyleSheet(font_value)

        info_od_lagoon = QLabel("OD:", self)
        info_od_lagoon.setGeometry(764, 203, 100, 25)
        info_od_lagoon.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        info_od_lagoon.setStyleSheet(font_value)


        # Slide Switches
        self.slide_switch_pump_1 = TapSwitch(self)
        self.slide_switch_pump_1.setGeometry(94, 263, 40, 20)
        self.slide_switch_pump_2 = TapSwitch(self)
        self.slide_switch_pump_2.setGeometry(654, 263, 40, 20)
        self.slide_switch_pump_3 = TapSwitch(self)
        self.slide_switch_pump_3.setGeometry(1127, 284, 40, 20)
        self.slide_switch_pump_4 = TapSwitch(self)
        self.slide_switch_pump_4.setGeometry(1127, 118, 40, 20)

        self.slide_switch_magneticStirrer_bioreactor = TapSwitch(self)
        self.slide_switch_magneticStirrer_bioreactor.setGeometry(267, 285, 40, 20)
        self.slide_switch_magneticStirrer_lagoon = TapSwitch(self)
        self.slide_switch_magneticStirrer_lagoon.setGeometry(794, 285, 40, 20)

        self.slide_switch_valve_bio2lag = TapSwitch(self)
        self.slide_switch_valve_bio2lag.setGeometry(520, 247, 40, 20)
        self.slide_switch_valve_sug2lag = TapSwitch(self)
        self.slide_switch_valve_sug2lag.setGeometry(548, 156, 40, 20)

        self.slide_switch_od_bioreactor = TapSwitch(self)
        self.slide_switch_od_bioreactor.setGeometry(190, 200, 40, 20)
        self.slide_switch_od_lagoon = TapSwitch(self)
        self.slide_switch_od_lagoon.setGeometry(717, 200, 40, 20)

        self.slide_switch_tempCtrl_bioreactor = TapSwitch(self)
        self.slide_switch_tempCtrl_bioreactor.setGeometry(379, 155, 40, 20)
        self.slide_switch_tempCtrl_lagoon = TapSwitch(self)
        self.slide_switch_tempCtrl_lagoon.setGeometry(906, 155, 40, 20)

        self.slide_switch_phtCount_Lagoon = TapSwitch(self)
        self.slide_switch_phtCount_Lagoon.setGeometry(906, 110, 40, 20)


        # Buttons
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
        self.pump_1_sp_update_btn = QPushButton("Update SP", self)
        self.pump_1_sp_update_btn.setGeometry(78, 357, 75, 20)
        self.pump_1_sp_update_btn.setStyleSheet(button_style)
        self.pump_2_sp_update_btn = QPushButton("Update SP", self)
        self.pump_2_sp_update_btn.setGeometry(638, 357, 75, 20)
        self.pump_2_sp_update_btn.setStyleSheet(button_style)
        self.pump_3_sp_update_btn = QPushButton("Update SP", self)
        self.pump_3_sp_update_btn.setGeometry(1111, 378, 75, 20)
        self.pump_3_sp_update_btn.setStyleSheet(button_style)
        self.pump_4_sp_update_btn = QPushButton("Update SP", self)
        self.pump_4_sp_update_btn.setGeometry(1111, 212, 75, 20)
        self.pump_4_sp_update_btn.setStyleSheet(button_style)

        self.magneticStirrer_bioreactor_sp_update_btn = QPushButton("Update SP", self)
        self.magneticStirrer_bioreactor_sp_update_btn.setGeometry(252, 381, 75, 20)
        self.magneticStirrer_bioreactor_sp_update_btn.setStyleSheet(button_style)
        self.magneticStirrer_lagoon_sp_update_btn = QPushButton("Update SP", self)
        self.magneticStirrer_lagoon_sp_update_btn.setGeometry(779, 381, 75, 20)
        self.magneticStirrer_lagoon_sp_update_btn.setStyleSheet(button_style)

        self.tempCtrl_bioreactor_sp_update_btn = QPushButton("Update SP", self)
        self.tempCtrl_bioreactor_sp_update_btn.setGeometry(454, 196, 75, 20)
        self.tempCtrl_bioreactor_sp_update_btn.setStyleSheet(button_style)
        self.tempCtrl_lagoon_sp_update_btn = QPushButton("Update SP", self)
        self.tempCtrl_lagoon_sp_update_btn.setGeometry(981, 196, 75, 20)
        self.tempCtrl_lagoon_sp_update_btn.setStyleSheet(button_style)

        # LED
        self.led_pump_1 = QLabel("⚪",self) #🔴🟢
        self.led_pump_1.setGeometry(79, 240, 20, 20)
        self.led_pump_2 = QLabel("⚪",self) #🔴🟢
        self.led_pump_2.setGeometry(639, 242, 20, 20)
        self.led_pump_3 = QLabel("⚪",self) #🔴🟢
        self.led_pump_3.setGeometry(1112, 261, 20, 20)
        self.led_pump_4 = QLabel("⚪",self) #🔴🟢
        self.led_pump_4.setGeometry(1112, 95, 20, 20)

        self.led_magneticStirrer_bioreactor = QLabel("⚪",self) #🔴🟢
        self.led_magneticStirrer_bioreactor.setGeometry(211, 252, 20, 20)
        self.led_magneticStirrer_lagoon = QLabel("⚪",self) #🔴🟢
        self.led_magneticStirrer_lagoon.setGeometry(738, 252, 20, 20)

        self.led_valve_bio2lag = QLabel("⚪",self) #🔴🟢
        self.led_valve_bio2lag.setGeometry(555, 215, 20, 20)
        self.led_valve_sug2lag = QLabel("⚪",self) #🔴🟢
        self.led_valve_sug2lag.setGeometry(583, 124, 20, 20)

        self.led_od_bioreactor = QLabel("⚪",self) #🔴🟢
        self.led_od_bioreactor.setGeometry(203, 141, 20, 20)
        self.led_od_lagoon = QLabel("⚪",self) #🔴🟢
        self.led_od_lagoon.setGeometry(730, 141, 20, 20)

        self.led_tempCtrl_bioreactor = QLabel("⚪",self) #🔴🟢
        self.led_tempCtrl_bioreactor.setGeometry(359, 157, 20, 20)
        self.led_tempCtrl_lagoon = QLabel("⚪",self) #🔴🟢
        self.led_tempCtrl_lagoon.setGeometry(886, 157, 20, 20)

        self.led_phtCount_lagoon = QLabel("⚪",self) #🔴🟢
        self.led_phtCount_lagoon.setGeometry(886, 112, 20, 20)

        self.led_overlight = QLabel("⚪",self) #🔴🟢
        self.led_overlight.setGeometry(915, 50, 22, 22)
        self.led_overlight.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self.led_overlight.setStyleSheet("""font-size: 18px;""")


        # Component signals (dynamic values that can change during runtime)
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

        self.pump_1_sp_edit = QLineEdit("0",self)
        self.pump_1_sp_edit.setGeometry(116, 302, 45, 20)
        self.pump_1_sp_edit.setStyleSheet(edit_style)
        self.pump_1_feedback = QLabel("FB: 0 rpm\n0 rpm, 0.000 ml/min", self)
        self.pump_1_feedback.setGeometry(29, 322, 170, 30)
        self.pump_1_feedback.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self.pump_1_feedback.setStyleSheet(font_small_value)

        self.pump_2_sp_edit = QLineEdit("0",self)
        self.pump_2_sp_edit.setGeometry(676, 302, 45, 20)
        self.pump_2_sp_edit.setStyleSheet(edit_style)
        self.pump_2_feedback = QLabel("FB: 0 rpm\n0 rpm, 0.000 ml/min", self)
        self.pump_2_feedback.setGeometry(592, 322, 170, 30)
        self.pump_2_feedback.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self.pump_2_feedback.setStyleSheet(font_small_value)

        self.pump_3_sp_edit = QLineEdit("0",self)
        self.pump_3_sp_edit.setGeometry(1149, 323, 45, 20)
        self.pump_3_sp_edit.setStyleSheet(edit_style)
        self.pump_3_feedback = QLabel("FB: 0 rpm\n0 rpm, 0.000 ml/min", self)
        self.pump_3_feedback.setGeometry(1062, 343, 170, 30)
        self.pump_3_feedback.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self.pump_3_feedback.setStyleSheet(font_small_value)

        self.pump_4_sp_edit = QLineEdit("0",self)
        self.pump_4_sp_edit.setGeometry(1149, 157, 45, 20)
        self.pump_4_sp_edit.setStyleSheet(edit_style)
        self.pump_4_feedback = QLabel("FB: 0 rpm\n0 rpm, 0.000 ml/min", self)
        self.pump_4_feedback.setGeometry(1062, 177, 170, 30)
        self.pump_4_feedback.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self.pump_4_feedback.setStyleSheet(font_small_value)

        self.magneticStirrer_bioreactor_sp_edit = QLineEdit("0",self)
        self.magneticStirrer_bioreactor_sp_edit.setGeometry(290, 326, 50, 20)
        self.magneticStirrer_bioreactor_sp_edit.setStyleSheet(edit_style)
        self.magneticStirrer_bioreactor_feedback = QLabel("FB: 0 rpm\n0 rpm, 00.00 %", self)
        self.magneticStirrer_bioreactor_feedback.setGeometry(203, 347, 170, 30)
        self.magneticStirrer_bioreactor_feedback.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self.magneticStirrer_bioreactor_feedback.setStyleSheet(font_small_value)

        self.magneticStirrer_lagoon_sp_edit = QLineEdit("0",self)
        self.magneticStirrer_lagoon_sp_edit.setGeometry(817, 326, 50, 20)
        self.magneticStirrer_lagoon_sp_edit.setStyleSheet(edit_style)
        self.magneticStirrer_lagoon_feedback = QLabel("FB: 0 rpm\n0 rpm, 00.00 %", self)
        self.magneticStirrer_lagoon_feedback.setGeometry(730, 347, 170, 30)
        self.magneticStirrer_lagoon_feedback.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self.magneticStirrer_lagoon_feedback.setStyleSheet(font_small_value)

        self.tempCtrl_bioreactor_feedback = QLabel("0.0 °C", self)
        self.tempCtrl_bioreactor_feedback.setGeometry(237, 178, 100, 20)
        self.tempCtrl_bioreactor_feedback.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self.tempCtrl_bioreactor_feedback.setStyleSheet(font_value_2)
        self.tempCtrl_bioreactor_sp_edit = QLineEdit("0.0",self)
        self.tempCtrl_bioreactor_sp_edit.setGeometry(401, 196, 50, 20)
        self.tempCtrl_bioreactor_sp_edit.setStyleSheet(edit_style)
        self.tempCtrl_bioreactor_feedback_sp_htr = QLabel("FB: 0.0 °C, HTR Duty: 00.0 %", self)
        self.tempCtrl_bioreactor_feedback_sp_htr.setGeometry(360, 215, 170, 20)
        self.tempCtrl_bioreactor_feedback_sp_htr.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.tempCtrl_bioreactor_feedback_sp_htr.setStyleSheet(font_small_value)

        self.tempCtrl_lagoon_feedback = QLabel("0.0 °C", self)
        self.tempCtrl_lagoon_feedback.setGeometry(764, 178, 100, 20)
        self.tempCtrl_lagoon_feedback.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self.tempCtrl_lagoon_feedback.setStyleSheet(font_value_2)
        self.tempCtrl_lagoon_sp_edit = QLineEdit("0.0",self)
        self.tempCtrl_lagoon_sp_edit.setGeometry(928, 196, 50, 20)
        self.tempCtrl_lagoon_sp_edit.setStyleSheet(edit_style)
        self.tempCtrl_lagoon_feedback_sp_htr = QLabel("FB: 0.0 °C, HTR Duty: 00.0 %", self)
        self.tempCtrl_lagoon_feedback_sp_htr.setGeometry(887, 215, 170, 20)
        self.tempCtrl_lagoon_feedback_sp_htr.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.tempCtrl_lagoon_feedback_sp_htr.setStyleSheet(font_small_value)

        self.od_bioreactor_feedback = QLabel("00.000", self)
        self.od_bioreactor_feedback.setGeometry(237, 228, 100, 25)
        self.od_bioreactor_feedback.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self.od_bioreactor_feedback.setStyleSheet(font_value_2)
        self.od_lagoon_feedback = QLabel("00.000", self)
        self.od_lagoon_feedback.setGeometry(764, 228, 100, 25)
        self.od_lagoon_feedback.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self.od_lagoon_feedback.setStyleSheet(font_value_2)

        self.phtCount_feedback = QLabel("00.000", self)
        self.phtCount_feedback.setGeometry(764, 128, 100, 25)
        self.phtCount_feedback.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self.phtCount_feedback.setStyleSheet(font_value_2)

    def connect_signals(self):
        """Connect signals to their respective slots"""
        self.evoflow_telemetry_updated.connect(self.update_telemetry)
        self.slide_switch_pump_1.toggled.connect(self.handle_pump_toggle)
        self.slide_switch_pump_2.toggled.connect(self.handle_pump_toggle)
        self.slide_switch_pump_3.toggled.connect(self.handle_pump_toggle)
        self.slide_switch_pump_4.toggled.connect(self.handle_pump_toggle)
        self.slide_switch_magneticStirrer_bioreactor.toggled.connect(self.handle_magneticStirrer_toggle)
        self.slide_switch_magneticStirrer_lagoon.toggled.connect(self.handle_magneticStirrer_toggle)
        self.slide_switch_od_bioreactor.toggled.connect(self.handle_od_toggle)
        self.slide_switch_od_lagoon.toggled.connect(self.handle_od_toggle)
        self.slide_switch_tempCtrl_bioreactor.toggled.connect(self.handle_tempCtrl_toggle)
        self.slide_switch_tempCtrl_lagoon.toggled.connect(self.handle_tempCtrl_toggle)
        self.slide_switch_valve_bio2lag.toggled.connect(self.handle_valve_toggle)
        self.slide_switch_valve_sug2lag.toggled.connect(self.handle_valve_toggle)
        self.slide_switch_phtCount_Lagoon.toggled.connect(self.handle_phtCount_toggle)

        self.pump_1_sp_update_btn.clicked.connect(self.handle_pump_sp_update)
        self.pump_2_sp_update_btn.clicked.connect(self.handle_pump_sp_update)
        self.pump_3_sp_update_btn.clicked.connect(self.handle_pump_sp_update)
        self.pump_4_sp_update_btn.clicked.connect(self.handle_pump_sp_update)
        self.magneticStirrer_bioreactor_sp_update_btn.clicked.connect(self.handle_magneticStirrer_sp_update)
        self.magneticStirrer_lagoon_sp_update_btn.clicked.connect(self.handle_magneticStirrer_sp_update)
        self.tempCtrl_bioreactor_sp_update_btn.clicked.connect(self.handle_tempCtrl_sp_update)
        self.tempCtrl_lagoon_sp_update_btn.clicked.connect(self.handle_tempCtrl_sp_update)

    def load_default_config(self):
        """Load flow rate conversion factors from config/settings.ini"""
        config = self.read_settings_file()
        self.pump_1_flow_conv = config.getfloat("flowRateConversionFactors", "pump_1")
        self.pump_2_flow_conv = config.getfloat("flowRateConversionFactors", "pump_2")
        self.pump_3_flow_conv = config.getfloat("flowRateConversionFactors", "pump_3")
        self.pump_4_flow_conv = config.getfloat("flowRateConversionFactors", "pump_4")

    def handle_pump_toggle(self, checked):
        """Handle all 4 pump toggles"""
        pump_1_status = self.slide_switch_pump_1.isChecked()
        pump_2_status = self.slide_switch_pump_2.isChecked()
        pump_3_status = self.slide_switch_pump_3.isChecked()
        pump_4_status = self.slide_switch_pump_4.isChecked()
        self.pump_on_off_requested.emit(pump_1_status, pump_2_status, pump_3_status, pump_4_status)

    def handle_magneticStirrer_toggle(self, checked):
        """Handle all magnetic stirrer toggles"""
        magneticStirrer_bioreactor_status = self.slide_switch_magneticStirrer_bioreactor.isChecked()
        magneticStirrer_lagoon_status = self.slide_switch_magneticStirrer_lagoon.isChecked()
        self.magneticStirrer_on_off_requested.emit(magneticStirrer_bioreactor_status, magneticStirrer_lagoon_status)

    def handle_od_toggle(self, checked):
        """Handle all OD toggles"""
        od_bioreactor_status = self.slide_switch_od_bioreactor.isChecked()
        od_lagoon_status = self.slide_switch_od_lagoon.isChecked()
        self.od_on_off_requested.emit(od_bioreactor_status, od_lagoon_status)

    def handle_tempCtrl_toggle(self, checked):
        """Handle all temperature controller toggles"""
        tempCtrl_bioreactor_status = self.slide_switch_tempCtrl_bioreactor.isChecked()
        tempCtrl_lagoon_status = self.slide_switch_tempCtrl_lagoon.isChecked()
        self.tempCtrl_on_off_requested.emit(tempCtrl_bioreactor_status, tempCtrl_lagoon_status)

    def handle_valve_toggle(self, checked):
        """Handle all valve toggles"""
        valve_bio2lag_status = self.slide_switch_valve_bio2lag.isChecked()
        valve_sug2lag_status = self.slide_switch_valve_sug2lag.isChecked()
        self.valve_on_off_requested.emit(valve_bio2lag_status, valve_sug2lag_status)

    def handle_phtCount_toggle(self, checked):
        """Handle photon counter toggle"""
        phtCount_lagoon_status = self.slide_switch_phtCount_Lagoon.isChecked()
        self.phtCount_on_off_requested.emit(phtCount_lagoon_status)

    def handle_pump_sp_update(self):
        """Handle all pump setpoint updates"""
        try:
            new_sp_1 = float(self.pump_1_sp_edit.text())
            new_sp_2 = float(self.pump_2_sp_edit.text())
            new_sp_3 = float(self.pump_3_sp_edit.text())
            new_sp_4 = float(self.pump_4_sp_edit.text())
            self.pump_sp_update_requested.emit(new_sp_1, new_sp_2, new_sp_3, new_sp_4)
        except ValueError:
            pass  # Invalid input, ignore
    
    def handle_magneticStirrer_sp_update(self):
        """Handle all magnetic stirrer setpoint updates"""
        try:
            new_sp_bioreactor = float(self.magneticStirrer_bioreactor_sp_edit.text())
            new_sp_lagoon = float(self.magneticStirrer_lagoon_sp_edit.text())
            self.magneticStirrer_sp_update_requested.emit(new_sp_bioreactor, new_sp_lagoon)
        except ValueError:
            pass  # Invalid input, ignore
    
    def handle_tempCtrl_sp_update(self):
        """Handle all temperature controller setpoint updates"""
        try:
            new_sp_bioreactor = float(self.tempCtrl_bioreactor_sp_edit.text())
            new_sp_lagoon = float(self.tempCtrl_lagoon_sp_edit.text())
            self.tempCtrl_sp_update_requested.emit(new_sp_bioreactor, new_sp_lagoon)
        except ValueError:
            pass  # Invalid input, ignore

    @Slot(EvoFlowTelemetry)
    def update_telemetry(self, evoflow_telemetry):
        """Update the widget based on incoming telemetry"""
        # Update pump 1
        if evoflow_telemetry.pump_1_status:
            self.led_pump_1.setText("🟢")
        else:
            self.led_pump_1.setText("🔴")
        self.pump_1_feedback.setText(f"FB: {evoflow_telemetry.pump_1_sp:.0f} rpm\n{evoflow_telemetry.pump_1_speed:.0f} rpm, {(self.pump_1_flow_conv * evoflow_telemetry.pump_1_speed):.3f} ml/min")
        # Update pump 2
        if evoflow_telemetry.pump_2_status:
            self.led_pump_2.setText("🟢")
        else:
            self.led_pump_2.setText("🔴")
        self.pump_2_feedback.setText(f"FB: {evoflow_telemetry.pump_2_sp:.0f} rpm\n{evoflow_telemetry.pump_2_speed:.0f} rpm, {(self.pump_2_flow_conv * evoflow_telemetry.pump_2_speed):.3f} ml/min")
        # Update pump 3
        if evoflow_telemetry.pump_3_status:
            self.led_pump_3.setText("🟢")
        else:
            self.led_pump_3.setText("🔴")
        self.pump_3_feedback.setText(f"FB: {evoflow_telemetry.pump_3_sp:.0f} rpm\n{evoflow_telemetry.pump_3_speed:.0f} rpm, {(self.pump_3_flow_conv * evoflow_telemetry.pump_3_speed):.3f} ml/min")
        # Update pump 4
        if evoflow_telemetry.pump_4_status:
            self.led_pump_4.setText("🟢")
        else:
            self.led_pump_4.setText("🔴")
        self.pump_4_feedback.setText(f"FB: {evoflow_telemetry.pump_4_sp:.0f} rpm\n{evoflow_telemetry.pump_4_speed:.0f} rpm, {(self.pump_4_flow_conv * evoflow_telemetry.pump_4_speed):.3f} ml/min")

        # Update magnetic stirrer bioreactor
        if evoflow_telemetry.magneticStirrer_bioreactor_status:
            self.led_magneticStirrer_bioreactor.setText("🟢")
        else:
            self.led_magneticStirrer_bioreactor.setText("🔴")
        self.magneticStirrer_bioreactor_feedback.setText(f"FB: {evoflow_telemetry.magneticStirrer_bioreactor_sp:.0f} rpm\n{evoflow_telemetry.magneticStirrer_bioreactor_speed:.0f} rpm, {evoflow_telemetry.magneticStirrer_bioreactor_fan_duty_cycle:.2f} %")
        # Update magnetic stirrer lagoon
        if evoflow_telemetry.magneticStirrer_lagoon_status:
            self.led_magneticStirrer_lagoon.setText("🟢")
        else:
            self.led_magneticStirrer_lagoon.setText("🔴")
        self.magneticStirrer_lagoon_feedback.setText(f"FB: {evoflow_telemetry.magneticStirrer_lagoon_sp:.0f} rpm\n{evoflow_telemetry.magneticStirrer_lagoon_speed:.0f} rpm, {evoflow_telemetry.magneticStirrer_lagoon_fan_duty_cycle:.2f} %")

        # Update temperature controller bioreactor
        if evoflow_telemetry.tempCtrl_bioreactor_status:
            self.led_tempCtrl_bioreactor.setText("🟢")
        else:
            self.led_tempCtrl_bioreactor.setText("🔴")
        self.tempCtrl_bioreactor_feedback.setText(f"{evoflow_telemetry.tempCtrl_bioreactor_value:.1f} °C")
        self.tempCtrl_bioreactor_feedback_sp_htr.setText(f"FB: {evoflow_telemetry.tempCtrl_bioreactor_sp:.1f} °C, HTR Duty: {evoflow_telemetry.tempCtrl_bioreactor_heater_duty_cycle:.1f} %")
        # Update temperature controller lagoon
        if evoflow_telemetry.tempCtrl_lagoon_status:
            self.led_tempCtrl_lagoon.setText("🟢")
        else:
            self.led_tempCtrl_lagoon.setText("🔴")
        self.tempCtrl_lagoon_feedback.setText(f"{evoflow_telemetry.tempCtrl_lagoon_value:.1f} °C")
        self.tempCtrl_lagoon_feedback_sp_htr.setText(f"FB: {evoflow_telemetry.tempCtrl_lagoon_sp:.1f} °C, HTR Duty: {evoflow_telemetry.tempCtrl_lagoon_heater_duty_cycle:.1f} %")

        # Update OD bioreactor
        if evoflow_telemetry.od_bioreactor_status:
            self.led_od_bioreactor.setText("🟢")
        else:
            self.led_od_bioreactor.setText("🔴")
        self.od_bioreactor_feedback.setText(f"{evoflow_telemetry.od_bioreactor_value:.2f}")
        # Update OD lagoon
        if evoflow_telemetry.od_lagoon_status:
            self.led_od_lagoon.setText("🟢")
        else:
            self.led_od_lagoon.setText("🔴")
        self.od_lagoon_feedback.setText(f"{evoflow_telemetry.od_lagoon_value:.2f}")

        # Update photon counter lagoon
        if evoflow_telemetry.phtCount_lagoon_status:
            self.led_phtCount_lagoon.setText("🟢")
        else:
            self.led_phtCount_lagoon.setText("🔴")
        self.phtCount_feedback.setText(f"{evoflow_telemetry.phtCount_lagoon_value/1000000:.2f} MHz")
        if evoflow_telemetry.phtCount_lagoon_overlight:
            self.led_overlight.setText("🔴")
        else:
            self.led_overlight.setText("⚪")

        # Update valve bio2lag
        if evoflow_telemetry.valve_bio2lag_status:
            self.led_valve_bio2lag.setText("🟢")
        else:
            self.led_valve_bio2lag.setText("🔴")
        # Update valve sug2lag
        if evoflow_telemetry.valve_sug2lag_status:
            self.led_valve_sug2lag.setText("🟢")
        else:
            self.led_valve_sug2lag.setText("🔴")

    def read_settings_file(self):
        """Load default configuration values from settings.ini"""
        # config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'settings.ini')      # for development
        config_path = resource_path("config/settings.ini")       # for bundling with PyInstaller
        config = configparser.ConfigParser()
        config.read(str(config_path))
        return config







