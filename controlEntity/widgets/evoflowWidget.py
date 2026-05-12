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

    def __init__(self, width: int=1200, height: int=720):
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
        background_img = QPixmap(os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "EvoFlow_GUI_Diagram.png"))
        scaled_background = background_img.scaled(self._width, self._height, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.background.setPixmap(scaled_background)


        # Info Labels (Static fonts, this won't change)
        font_component = """font-weight: bold; color: Orange;"""
        font_description = """font-weight: bold; color: LightGreen;"""
        font_value = """font-weight: bold; font-size: 18px; color: #575757;"""
        font_value_2 = """font-weight: bold; font-size: 18px; color: #0070a3;"""

        info_pump_1 = QLabel("Pump 1", self)
        info_pump_1.setGeometry(104, 307, 50, 20)
        info_pump_1.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        info_pump_1.setStyleSheet(font_component)
        info_pump_1_sp = QLabel("SP(rpm):", self)
        info_pump_1_sp.setGeometry(29, 327, 100, 20)
        info_pump_1_sp.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        info_pump_2 = QLabel("Pump 2", self)
        info_pump_2.setGeometry(713, 307, 50, 20)
        info_pump_2.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        info_pump_2.setStyleSheet(font_component)
        info_pump_2_sp = QLabel("SP(rpm):", self)
        info_pump_2_sp.setGeometry(638, 327, 100, 20)
        info_pump_2_sp.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        info_pump_3 = QLabel("Pump 3", self)
        info_pump_3.setGeometry(196, 503, 50, 20)
        info_pump_3.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        info_pump_3.setStyleSheet(font_component)
        info_pump_3_sp = QLabel("SP(rpm):", self)
        info_pump_3_sp.setGeometry(121, 523, 100, 20)
        info_pump_3_sp.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        info_pump_4 = QLabel("Pump 4", self)
        info_pump_4.setGeometry(1003, 503, 50, 20)
        info_pump_4.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        info_pump_4.setStyleSheet(font_component)
        info_pump_4_sp = QLabel("SP(rpm):", self)
        info_pump_4_sp.setGeometry(928, 523, 100, 20)
        info_pump_4_sp.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        info_magneticStirrer_bioreactor = QLabel("Magnetic Stirrer", self)
        info_magneticStirrer_bioreactor.setGeometry(268, 333, 100, 20)
        info_magneticStirrer_bioreactor.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        info_magneticStirrer_bioreactor.setStyleSheet(font_component)
        info_sp_magneticStirrer_bioreactor = QLabel("SP(rpm):", self)
        info_sp_magneticStirrer_bioreactor.setGeometry(216, 353, 100, 20)
        info_sp_magneticStirrer_bioreactor.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        info_magneticStirrer_lagoon = QLabel("Magnetic Stirrer", self)
        info_magneticStirrer_lagoon.setGeometry(842, 333, 100, 20)
        info_magneticStirrer_lagoon.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        info_magneticStirrer_lagoon.setStyleSheet(font_component)
        info_sp_magneticStirrer_lagoon = QLabel("SP(rpm):", self)
        info_sp_magneticStirrer_lagoon.setGeometry(790, 353, 100, 20)
        info_sp_magneticStirrer_lagoon.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        info_od_bioreactor = QLabel("Optical\nDensity", self)
        info_od_bioreactor.setGeometry(182, 178, 100, 40)
        info_od_bioreactor.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        info_od_bioreactor.setStyleSheet(font_component)

        info_od_lagoon = QLabel("Optical\nDensity", self)
        info_od_lagoon.setGeometry(756, 178, 100, 40)
        info_od_lagoon.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        info_od_lagoon.setStyleSheet(font_component)

        info_tempCtrl_bioreactor = QLabel("Temp Ctrl", self)
        info_tempCtrl_bioreactor.setGeometry(380, 183, 100, 40)
        info_tempCtrl_bioreactor.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        info_tempCtrl_bioreactor.setStyleSheet(font_component)
        info_sp_tempCtrl_bioreactor = QLabel("SP(°C):", self)
        info_sp_tempCtrl_bioreactor.setGeometry(328, 213, 100, 20)
        info_sp_tempCtrl_bioreactor.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        info_tempCtrl_lagoon = QLabel("Temp Ctrl", self)
        info_tempCtrl_lagoon.setGeometry(954, 183, 100, 40)
        info_tempCtrl_lagoon.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        info_tempCtrl_lagoon.setStyleSheet(font_component)
        info_sp_tempCtrl_lagoon = QLabel("SP(°C):", self)
        info_sp_tempCtrl_lagoon.setGeometry(902, 213, 100, 20)
        info_sp_tempCtrl_lagoon.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        info_phtCounter_lagoon = QLabel("Photon Counter", self)
        info_phtCounter_lagoon.setGeometry(954, 138, 100, 40)
        info_phtCounter_lagoon.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        info_phtCounter_lagoon.setStyleSheet(font_component)

        info_valve_bio2lag = QLabel("Valve\nBio2Lag", self)
        info_valve_bio2lag.setGeometry(542, 293, 100, 40)
        info_valve_bio2lag.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        info_valve_bio2lag.setStyleSheet(font_component)

        info_valve_sug2lag = QLabel("Valve\nSug2Lag", self)
        info_valve_sug2lag.setGeometry(573, 193, 100, 40)
        info_valve_sug2lag.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        info_valve_sug2lag.setStyleSheet(font_component)

        info_from_medium = QLabel("From Medium", self)
        info_from_medium.setGeometry(15, 236, 100, 20)
        info_from_medium.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        info_from_medium.setStyleSheet(font_description)

        info_to_waste = QLabel("To Waste", self)
        info_to_waste.setGeometry(358, 455, 100, 20)
        info_to_waste.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        info_to_waste.setStyleSheet(font_description)

        info_to_waste_sample = QLabel("To Waste / Sample", self)
        info_to_waste_sample.setGeometry(718, 455, 120, 20)
        info_to_waste_sample.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        info_to_waste_sample.setStyleSheet(font_description)

        info_overlight = QLabel("Overlight\nDetected", self)
        info_overlight.setGeometry(944, 88, 120, 40)
        info_overlight.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        info_overlight.setStyleSheet(font_component)

        info_bioreactor = QLabel("Bioreactor", self)
        info_bioreactor.setGeometry(219, 8, 200, 35)
        info_bioreactor.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        info_bioreactor.setStyleSheet("""font-weight: bold; font-size: 24px;""")

        info_lagoon = QLabel("Lagoon", self)
        info_lagoon.setGeometry(791, 8, 200, 35)
        info_lagoon.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        info_lagoon.setStyleSheet("""font-weight: bold; font-size: 24px;""")

        info_sugar = QLabel("Sugar", self)
        info_sugar.setGeometry(479, 54, 100, 25)
        info_sugar.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        info_sugar.setStyleSheet("""font-weight: bold; font-size: 18px;""")

        info_waste = QLabel("Waste", self)
        info_waste.setGeometry(405, 632, 100, 25)
        info_waste.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        info_waste.setStyleSheet("""font-weight: bold; font-size: 18px;""")

        info_temp_bioreactor = QLabel("Temp:", self)
        info_temp_bioreactor.setGeometry(267, 158, 100, 25)
        info_temp_bioreactor.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        info_temp_bioreactor.setStyleSheet(font_value)

        info_od_bioreactor = QLabel("OD:", self)
        info_od_bioreactor.setGeometry(267, 218, 100, 25)
        info_od_bioreactor.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        info_od_bioreactor.setStyleSheet(font_value)

        info_phtCount_lagoon = QLabel("PHT Count:", self)
        info_phtCount_lagoon.setGeometry(841, 98, 100, 25)
        info_phtCount_lagoon.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        info_phtCount_lagoon.setStyleSheet(font_value)

        info_temp_lagoon = QLabel("Temp:", self)
        info_temp_lagoon.setGeometry(841, 158, 100, 25)
        info_temp_lagoon.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        info_temp_lagoon.setStyleSheet(font_value)

        info_od_lagoon = QLabel("OD:", self)
        info_od_lagoon.setGeometry(841, 218, 100, 25)
        info_od_lagoon.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        info_od_lagoon.setStyleSheet(font_value)


        # Slide Switches
        self.slide_switch_pump_1 = TapSwitch(self)
        self.slide_switch_pump_1.setGeometry(108, 286, 40, 20)
        self.slide_switch_pump_2 = TapSwitch(self)
        self.slide_switch_pump_2.setGeometry(717, 286, 40, 20)
        self.slide_switch_pump_3 = TapSwitch(self)
        self.slide_switch_pump_3.setGeometry(200, 482, 40, 20)
        self.slide_switch_pump_4 = TapSwitch(self)
        self.slide_switch_pump_4.setGeometry(1007, 482, 40, 20)

        self.slide_switch_magneticStirrer_bioreactor = TapSwitch(self)
        self.slide_switch_magneticStirrer_bioreactor.setGeometry(296, 313, 40, 20)
        self.slide_switch_magneticStirrer_lagoon = TapSwitch(self)
        self.slide_switch_magneticStirrer_lagoon.setGeometry(870, 313, 40, 20)

        self.slide_switch_valve_bio2lag = TapSwitch(self)
        self.slide_switch_valve_bio2lag.setGeometry(572, 273, 40, 20)
        self.slide_switch_valve_sug2lag = TapSwitch(self)
        self.slide_switch_valve_sug2lag.setGeometry(603, 174, 40, 20)

        self.slide_switch_od_bioreactor = TapSwitch(self)
        self.slide_switch_od_bioreactor.setGeometry(212, 220, 40, 20)
        self.slide_switch_od_lagoon = TapSwitch(self)
        self.slide_switch_od_lagoon.setGeometry(786, 220, 40, 20)

        self.slide_switch_tempCtrl_bioreactor = TapSwitch(self)
        self.slide_switch_tempCtrl_bioreactor.setGeometry(410, 173, 40, 20)
        self.slide_switch_tempCtrl_lagoon = TapSwitch(self)
        self.slide_switch_tempCtrl_lagoon.setGeometry(984, 173, 40, 20)

        self.slide_switch_phtCount_Lagoon = TapSwitch(self)
        self.slide_switch_phtCount_Lagoon.setGeometry(984, 128, 40, 20)


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
        self.pump_1_sp_update_btn.setGeometry(92, 383, 75, 20)
        self.pump_1_sp_update_btn.setStyleSheet(button_style)
        self.pump_2_sp_update_btn = QPushButton("Update SP", self)
        self.pump_2_sp_update_btn.setGeometry(701, 383, 75, 20)
        self.pump_2_sp_update_btn.setStyleSheet(button_style)
        self.pump_3_sp_update_btn = QPushButton("Update SP", self)
        self.pump_3_sp_update_btn.setGeometry(182, 579, 75, 20)
        self.pump_3_sp_update_btn.setStyleSheet(button_style)
        self.pump_4_sp_update_btn = QPushButton("Update SP", self)
        self.pump_4_sp_update_btn.setGeometry(991, 579, 75, 20)
        self.pump_4_sp_update_btn.setStyleSheet(button_style)

        self.magneticStirrer_bioreactor_sp_update_btn = QPushButton("Update SP", self)
        self.magneticStirrer_bioreactor_sp_update_btn.setGeometry(281, 409, 75, 20)
        self.magneticStirrer_bioreactor_sp_update_btn.setStyleSheet(button_style)
        self.magneticStirrer_lagoon_sp_update_btn = QPushButton("Update SP", self)
        self.magneticStirrer_lagoon_sp_update_btn.setGeometry(855, 409, 75, 20)
        self.magneticStirrer_lagoon_sp_update_btn.setStyleSheet(button_style)

        self.tempCtrl_bioreactor_sp_update_btn = QPushButton("Update SP", self)
        self.tempCtrl_bioreactor_sp_update_btn.setGeometry(485, 214, 75, 20)
        self.tempCtrl_bioreactor_sp_update_btn.setStyleSheet(button_style)
        self.tempCtrl_lagoon_sp_update_btn = QPushButton("Update SP", self)
        self.tempCtrl_lagoon_sp_update_btn.setGeometry(1059, 214, 75, 20)
        self.tempCtrl_lagoon_sp_update_btn.setStyleSheet(button_style)

        # LED
        self.led_pump_1 = QLabel("⚪",self) #🔴🟢
        self.led_pump_1.setGeometry(90, 265, 20, 20)
        self.led_pump_2 = QLabel("⚪",self) #🔴🟢
        self.led_pump_2.setGeometry(699, 265, 20, 20)
        self.led_pump_3 = QLabel("⚪",self) #🔴🟢
        self.led_pump_3.setGeometry(182, 461, 20, 20)
        self.led_pump_4 = QLabel("⚪",self) #🔴🟢
        self.led_pump_4.setGeometry(989, 461, 20, 20)

        self.led_magneticStirrer_bioreactor = QLabel("⚪",self) #🔴🟢
        self.led_magneticStirrer_bioreactor.setGeometry(240, 280, 20, 20)
        self.led_magneticStirrer_lagoon = QLabel("⚪",self) #🔴🟢
        self.led_magneticStirrer_lagoon.setGeometry(814, 280, 20, 20)

        self.led_valve_bio2lag = QLabel("⚪",self) #🔴🟢
        self.led_valve_bio2lag.setGeometry(554, 260, 20, 20)
        self.led_valve_sug2lag = QLabel("⚪",self) #🔴🟢
        self.led_valve_sug2lag.setGeometry(585, 161, 20, 20)

        self.led_od_bioreactor = QLabel("⚪",self) #🔴🟢
        self.led_od_bioreactor.setGeometry(225, 161, 20, 20)
        self.led_od_lagoon = QLabel("⚪",self) #🔴🟢
        self.led_od_lagoon.setGeometry(799, 161, 20, 20)

        self.led_tempCtrl_bioreactor = QLabel("⚪",self) #🔴🟢
        self.led_tempCtrl_bioreactor.setGeometry(390, 175, 20, 20)
        self.led_tempCtrl_lagoon = QLabel("⚪",self) #🔴🟢
        self.led_tempCtrl_lagoon.setGeometry(964, 175, 20, 20)

        self.led_phtCount_lagoon = QLabel("⚪",self) #🔴🟢
        self.led_phtCount_lagoon.setGeometry(964, 130, 20, 20)

        self.led_overlight = QLabel("⚪",self) #🔴🟢
        self.led_overlight.setGeometry(993, 68, 22, 22)
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

        self.pump_1_sp_edit = QLineEdit("00.00",self)
        self.pump_1_sp_edit.setGeometry(132, 328, 45, 20)
        self.pump_1_sp_edit.setStyleSheet(edit_style)
        self.pump_1_feedback = QLabel("FB: 00.00 rpm\n00.00 rpm, 0.000 ml/min", self)
        self.pump_1_feedback.setGeometry(43, 349, 170, 30)
        self.pump_1_feedback.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)

        self.pump_2_sp_edit = QLineEdit("00.00",self)
        self.pump_2_sp_edit.setGeometry(741, 328, 45, 20)
        self.pump_2_sp_edit.setStyleSheet(edit_style)
        self.pump_2_feedback = QLabel("FB: 00.00 rpm\n00.00 rpm, 0.000 ml/min", self)
        self.pump_2_feedback.setGeometry(652, 349, 170, 30)
        self.pump_2_feedback.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)

        self.pump_3_sp_edit = QLineEdit("00.00",self)
        self.pump_3_sp_edit.setGeometry(224, 524, 45, 20)
        self.pump_3_sp_edit.setStyleSheet(edit_style)
        self.pump_3_feedback = QLabel("FB: 00.00 rpm\n00.00 rpm, 0.000 ml/min", self)
        self.pump_3_feedback.setGeometry(135, 545, 170, 30)
        self.pump_3_feedback.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)

        self.pump_4_sp_edit = QLineEdit("00.00",self)
        self.pump_4_sp_edit.setGeometry(1031, 524, 45, 20)
        self.pump_4_sp_edit.setStyleSheet(edit_style)
        self.pump_4_feedback = QLabel("FB: 00.00 rpm\n00.00 rpm, 0.000 ml/min", self)
        self.pump_4_feedback.setGeometry(942, 545, 170, 30)
        self.pump_4_feedback.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)

        self.magneticStirrer_bioreactor_sp_edit = QLineEdit("00.00",self)
        self.magneticStirrer_bioreactor_sp_edit.setGeometry(319, 354, 50, 20)
        self.magneticStirrer_bioreactor_sp_edit.setStyleSheet(edit_style)
        self.magneticStirrer_bioreactor_feedback = QLabel("FB: 00.00 rpm\n00.00 rpm, 00.00 %", self)
        self.magneticStirrer_bioreactor_feedback.setGeometry(232, 375, 170, 30)
        self.magneticStirrer_bioreactor_feedback.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)

        self.magneticStirrer_lagoon_sp_edit = QLineEdit("00.00",self)
        self.magneticStirrer_lagoon_sp_edit.setGeometry(893, 354, 50, 20)
        self.magneticStirrer_lagoon_sp_edit.setStyleSheet(edit_style)
        self.magneticStirrer_lagoon_feedback = QLabel("FB: 00.00 rpm\n00.00 rpm, 00.00 %", self)
        self.magneticStirrer_lagoon_feedback.setGeometry(806, 375, 170, 30)
        self.magneticStirrer_lagoon_feedback.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)

        self.tempCtrl_bioreactor_feedback = QLabel("00.00 °C", self)
        self.tempCtrl_bioreactor_feedback.setGeometry(267, 193, 100, 20)
        self.tempCtrl_bioreactor_feedback.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self.tempCtrl_bioreactor_feedback.setStyleSheet(font_value_2)
        self.tempCtrl_bioreactor_sp_edit = QLineEdit("00.00",self)
        self.tempCtrl_bioreactor_sp_edit.setGeometry(432, 214, 50, 20)
        self.tempCtrl_bioreactor_sp_edit.setStyleSheet(edit_style)
        self.tempCtrl_bioreactor_feedback_sp_htr = QLabel("FB: 00.00 °C, HTR Duty: 00.00 %", self)
        self.tempCtrl_bioreactor_feedback_sp_htr.setGeometry(391, 233, 170, 20)
        self.tempCtrl_bioreactor_feedback_sp_htr.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.tempCtrl_lagoon_feedback = QLabel("00.00 °C", self)
        self.tempCtrl_lagoon_feedback.setGeometry(841, 193, 100, 20)
        self.tempCtrl_lagoon_feedback.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self.tempCtrl_lagoon_feedback.setStyleSheet(font_value_2)
        self.tempCtrl_lagoon_sp_edit = QLineEdit("00.00",self)
        self.tempCtrl_lagoon_sp_edit.setGeometry(1006, 214, 50, 20)
        self.tempCtrl_lagoon_sp_edit.setStyleSheet(edit_style)
        self.tempCtrl_lagoon_feedback_sp_htr = QLabel("FB: 00.00 °C, HTR Duty: 00.00 %", self)
        self.tempCtrl_lagoon_feedback_sp_htr.setGeometry(965, 233, 170, 20)
        self.tempCtrl_lagoon_feedback_sp_htr.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.od_bioreactor_feedback = QLabel("00.000", self)
        self.od_bioreactor_feedback.setGeometry(267, 248, 100, 25)
        self.od_bioreactor_feedback.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self.od_bioreactor_feedback.setStyleSheet(font_value_2)
        self.od_lagoon_feedback = QLabel("00.000", self)
        self.od_lagoon_feedback.setGeometry(841, 248, 100, 25)
        self.od_lagoon_feedback.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self.od_lagoon_feedback.setStyleSheet(font_value_2)

        self.phtCount_feedback = QLabel("00.000", self)
        self.phtCount_feedback.setGeometry(841, 128, 100, 25)
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
        self.pump_1_feedback.setText(f"FB: {evoflow_telemetry.pump_1_sp:.2f} rpm\n{evoflow_telemetry.pump_1_speed:.2f} rpm, {(self.pump_1_flow_conv * evoflow_telemetry.pump_1_speed):.3f} ml/min")
        # Update pump 2
        if evoflow_telemetry.pump_2_status:
            self.led_pump_2.setText("🟢")
        else:
            self.led_pump_2.setText("🔴")
        self.pump_2_feedback.setText(f"FB: {evoflow_telemetry.pump_2_sp:.2f} rpm\n{evoflow_telemetry.pump_2_speed:.2f} rpm, {(self.pump_2_flow_conv * evoflow_telemetry.pump_2_speed):.3f} ml/min")
        # Update pump 3
        if evoflow_telemetry.pump_3_status:
            self.led_pump_3.setText("🟢")
        else:
            self.led_pump_3.setText("🔴")
        self.pump_3_feedback.setText(f"FB: {evoflow_telemetry.pump_3_sp:.2f} rpm\n{evoflow_telemetry.pump_3_speed:.2f} rpm, {(self.pump_3_flow_conv * evoflow_telemetry.pump_3_speed):.3f} ml/min")
        # Update pump 4
        if evoflow_telemetry.pump_4_status:
            self.led_pump_4.setText("🟢")
        else:
            self.led_pump_4.setText("🔴")
        self.pump_4_feedback.setText(f"FB: {evoflow_telemetry.pump_4_sp:.2f} rpm\n{evoflow_telemetry.pump_4_speed:.2f} rpm, {(self.pump_4_flow_conv * evoflow_telemetry.pump_4_speed):.3f} ml/min")

        # Update magnetic stirrer bioreactor
        if evoflow_telemetry.magneticStirrer_bioreactor_status:
            self.led_magneticStirrer_bioreactor.setText("🟢")
        else:
            self.led_magneticStirrer_bioreactor.setText("🔴")
        self.magneticStirrer_bioreactor_feedback.setText(f"FB: {evoflow_telemetry.magneticStirrer_bioreactor_sp:.2f} rpm\n{evoflow_telemetry.magneticStirrer_bioreactor_speed:.2f} rpm, {evoflow_telemetry.magneticStirrer_bioreactor_fan_duty_cycle:.2f} %")
        # Update magnetic stirrer lagoon
        if evoflow_telemetry.magneticStirrer_lagoon_status:
            self.led_magneticStirrer_lagoon.setText("🟢")
        else:
            self.led_magneticStirrer_lagoon.setText("🔴")
        self.magneticStirrer_lagoon_feedback.setText(f"FB: {evoflow_telemetry.magneticStirrer_lagoon_sp:.2f} rpm\n{evoflow_telemetry.magneticStirrer_lagoon_speed:.2f} rpm, {evoflow_telemetry.magneticStirrer_lagoon_fan_duty_cycle:.2f} %")

        # Update temperature controller bioreactor
        if evoflow_telemetry.tempCtrl_bioreactor_status:
            self.led_tempCtrl_bioreactor.setText("🟢")
        else:
            self.led_tempCtrl_bioreactor.setText("🔴")
        self.tempCtrl_bioreactor_feedback.setText(f"{evoflow_telemetry.tempCtrl_bioreactor_value:.2f} °C")
        self.tempCtrl_bioreactor_feedback_sp_htr.setText(f"FB: {evoflow_telemetry.tempCtrl_bioreactor_sp:.2f} °C, HTR Duty: {evoflow_telemetry.tempCtrl_bioreactor_heater_duty_cycle:.2f} %")
        # Update temperature controller lagoon
        if evoflow_telemetry.tempCtrl_lagoon_status:
            self.led_tempCtrl_lagoon.setText("🟢")
        else:
            self.led_tempCtrl_lagoon.setText("🔴")
        self.tempCtrl_lagoon_feedback.setText(f"{evoflow_telemetry.tempCtrl_lagoon_value:.2f} °C")
        self.tempCtrl_lagoon_feedback_sp_htr.setText(f"FB: {evoflow_telemetry.tempCtrl_lagoon_sp:.2f} °C, HTR Duty: {evoflow_telemetry.tempCtrl_lagoon_heater_duty_cycle:.2f} %")

        # Update OD bioreactor
        if evoflow_telemetry.od_bioreactor_status:
            self.led_od_bioreactor.setText("🟢")
        else:
            self.led_od_bioreactor.setText("🔴")
        self.od_bioreactor_feedback.setText(f"{evoflow_telemetry.od_bioreactor_value:.3f}")
        # Update OD lagoon
        if evoflow_telemetry.od_lagoon_status:
            self.led_od_lagoon.setText("🟢")
        else:
            self.led_od_lagoon.setText("🔴")
        self.od_lagoon_feedback.setText(f"{evoflow_telemetry.od_lagoon_value:.3f}")

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







