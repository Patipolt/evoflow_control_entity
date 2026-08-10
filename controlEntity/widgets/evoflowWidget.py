"""
EvoFlowWidget for graphical representation of the EvoFlow system

Project: EvoFlow Innosuisse
Author: Patipol Thanuphol, Scientific Researcher at ZHAW — thau@zhaw.ch | patipol.thanuphol@zhaw.ch
Created: April 2026
"""

import time
import os
import configparser
import numpy as np
from PySide6.QtWidgets import QApplication, QHBoxLayout, QMainWindow, QMessageBox, QWidget, QVBoxLayout, QLCDNumber, QLineEdit, QComboBox, QCalendarWidget, QTextEdit, QTimeEdit
from PySide6.QtWidgets import QPushButton, QGroupBox, QTabWidget, QTableView, QMenuBar, QStatusBar, QLabel, QCheckBox, QColorDialog
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import Qt, QFile, QTimer, QDate, QTime, QIODeviceBase, QEvent, Signal, Slot, QObject
from PySide6.QtGui import QKeyEvent, QTextCharFormat, QStandardItemModel, QStandardItem, QWheelEvent, QCloseEvent, QAction, QPixmap

from controlEntity.widgets.TapSwitchWidget import TapSwitch
from controlEntity.utils import resource_path
from evoflow.device.evoflow import EvoFlowTelemetry

magneticStirrer_swapping_mode_enabled = True


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

    pump_sp_update_requested = Signal(float, float, float, float)
    magneticStirrer_sp_update_requested = Signal(float, float)
    tempCtrl_sp_update_requested = Signal(float, float)

    reset_evoflow_requested = Signal()


    def __init__(self, width: int=1800, height: int=450):
        """"Initialize the EvoFlowWidget"""
        super().__init__()
        self._width: int = width
        self._height: int = height
        self._evoflow_comm_led_hold_ms = 75
        self._evoflow_comm_led_reset_timer = QTimer(self)
        self._evoflow_comm_led_reset_timer.setSingleShot(True)
        self._evoflow_comm_led_reset_timer.timeout.connect(self._reset_evoflow_comm_led)
        self.load_default_config()
        self.setup_ui()
        self.connect_signals()

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
        font_component = """font-weight: bold; color: Orange; font-size: 11px;"""
        font_description = """font-weight: bold; color: LightGreen; font-size: 11px;"""
        font_value = """font-weight: bold; font-size: 16px; color: #575757;"""
        font_value_2 = """font-weight: bold; font-size: 16px; color: #0070a3;"""
        font_small_value = """color: White; font-size: 11px;"""

        info_pump_1 = QLabel("Pump 1", self)
        info_pump_1.setGeometry(90, 283, 50, 20)
        info_pump_1.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        info_pump_1.setStyleSheet(font_component)
        info_pump_1_sp = QLabel("SP(ul/m):", self)
        info_pump_1_sp.setGeometry(15, 300, 100, 20)
        info_pump_1_sp.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        info_pump_1_sp.setStyleSheet(font_small_value)

        info_pump_2 = QLabel("Pump 2", self)
        info_pump_2.setGeometry(650, 283, 50, 20)
        info_pump_2.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        info_pump_2.setStyleSheet(font_component)
        info_pump_2_sp = QLabel("SP(ul/m):", self)
        info_pump_2_sp.setGeometry(575, 300, 100, 20)
        info_pump_2_sp.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        info_pump_2_sp.setStyleSheet(font_small_value)

        info_pump_3 = QLabel("Pump 3", self)
        info_pump_3.setGeometry(1123, 304, 50, 20)
        info_pump_3.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        info_pump_3.setStyleSheet(font_component)
        info_pump_3_sp = QLabel("SP(ul/m):", self)
        info_pump_3_sp.setGeometry(1048, 321, 100, 20)
        info_pump_3_sp.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        info_pump_3_sp.setStyleSheet(font_small_value)

        info_pump_4 = QLabel("Pump 4", self)
        info_pump_4.setGeometry(1123, 138, 50, 20)
        info_pump_4.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        info_pump_4.setStyleSheet(font_component)
        info_pump_4_sp = QLabel("SP(ul/m):", self)
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
        info_to_waste.setGeometry(1085, 220, 120, 20)
        info_to_waste.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
        info_to_waste.setStyleSheet(font_description)

        info_to_waste_sample = QLabel("To Waste / Sample", self)
        info_to_waste_sample.setGeometry(1085, 53, 120, 20)
        info_to_waste_sample.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
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
        config = self.read_settings_file()

        self.slide_switch_pump_1 = TapSwitch(self)
        self.slide_switch_pump_1.setGeometry(94, 263, 40, 20)
        self.slide_switch_pump_1.setChecked(config.getboolean('defaultComponentStatus', 'pump1_status', fallback=False))
        self.slide_switch_pump_2 = TapSwitch(self)
        self.slide_switch_pump_2.setGeometry(654, 263, 40, 20)
        self.slide_switch_pump_2.setChecked(config.getboolean('defaultComponentStatus', 'pump2_status', fallback=False))
        self.slide_switch_pump_3 = TapSwitch(self)
        self.slide_switch_pump_3.setGeometry(1127, 284, 40, 20)
        self.slide_switch_pump_3.setChecked(config.getboolean('defaultComponentStatus', 'pump3_status', fallback=False))
        self.slide_switch_pump_4 = TapSwitch(self)
        self.slide_switch_pump_4.setGeometry(1127, 118, 40, 20)
        self.slide_switch_pump_4.setChecked(config.getboolean('defaultComponentStatus', 'pump4_status', fallback=False))

        self.slide_switch_magneticStirrer_bioreactor = TapSwitch(self)
        self.slide_switch_magneticStirrer_bioreactor.setGeometry(267, 285, 40, 20)
        self.slide_switch_magneticStirrer_bioreactor.setChecked(config.getboolean('defaultComponentStatus', 'magneticStirrer_bioreactor_status', fallback=False))
        self.slide_switch_magneticStirrer_lagoon = TapSwitch(self)
        self.slide_switch_magneticStirrer_lagoon.setGeometry(794, 285, 40, 20)
        self.slide_switch_magneticStirrer_lagoon.setChecked(config.getboolean('defaultComponentStatus', 'magneticStirrer_lagoon_status', fallback=False))

        self.slide_switch_valve_bio2lag = TapSwitch(self)
        self.slide_switch_valve_bio2lag.setGeometry(520, 247, 40, 20)
        self.slide_switch_valve_bio2lag.setChecked(config.getboolean('defaultComponentStatus', 'bio2lagValve_status', fallback=False))
        self.slide_switch_valve_sug2lag = TapSwitch(self)
        self.slide_switch_valve_sug2lag.setGeometry(548, 156, 40, 20)
        self.slide_switch_valve_sug2lag.setChecked(config.getboolean('defaultComponentStatus', 'sug2lagValve_status', fallback=False))

        self.slide_switch_od_bioreactor = TapSwitch(self)
        self.slide_switch_od_bioreactor.setGeometry(190, 200, 40, 20)
        self.slide_switch_od_bioreactor.setChecked(config.getboolean('defaultComponentStatus', 'od_bioreactor_status', fallback=False))
        self.slide_switch_od_lagoon = TapSwitch(self)
        self.slide_switch_od_lagoon.setGeometry(717, 200, 40, 20)
        self.slide_switch_od_lagoon.setChecked(config.getboolean('defaultComponentStatus', 'od_lagoon_status', fallback=False))
        # In case of OD measurement can not be activated at the same time as photon counter
        self.slide_switch_od_lagoon.setEnabled(config.getboolean('defaultComponentStatus', 'od_lagoon_enabled', fallback=False))

        self.slide_switch_tempCtrl_bioreactor = TapSwitch(self)
        self.slide_switch_tempCtrl_bioreactor.setGeometry(379, 155, 40, 20)
        self.slide_switch_tempCtrl_bioreactor.setChecked(config.getboolean('defaultComponentStatus', 'tempCtrl_bioreactor_status', fallback=False))
        self.slide_switch_tempCtrl_lagoon = TapSwitch(self)
        self.slide_switch_tempCtrl_lagoon.setGeometry(906, 155, 40, 20)
        self.slide_switch_tempCtrl_lagoon.setChecked(config.getboolean('defaultComponentStatus', 'tempCtrl_lagoon_status', fallback=False))

        self.slide_switch_phtCount_Lagoon = TapSwitch(self)
        self.slide_switch_phtCount_Lagoon.setGeometry(906, 110, 40, 20)
        self.slide_switch_phtCount_Lagoon.setChecked(config.getboolean('defaultComponentStatus', 'phtCount_status', fallback=False))


        # Buttons
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
      
        # Combined button design
        groupbox_style = """
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                color: #ffffff;
                border: 2px solid #ffffff;
                border-radius: 10px;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0px 3px;
            }
        """

        evoflow_control_groupbox = QGroupBox("EvoFlow Control", self)
        evoflow_control_groupbox.setStyleSheet(groupbox_style)
        evoflow_control_groupbox.setGeometry(1245, 290, 250, 150)
        evoflow_control_V_layout = QVBoxLayout(evoflow_control_groupbox)

        self.pumps_sp_update_btn = QPushButton("Update Pump Set Points", evoflow_control_groupbox)
        self.pumps_sp_update_btn.setStyleSheet(button_style)
        self.pumps_sp_update_btn.setMinimumHeight(24)
        self.tempCtrls_sp_update_btn = QPushButton("Update Temp. Ctrl Set Points", evoflow_control_groupbox)
        self.tempCtrls_sp_update_btn.setStyleSheet(button_style)
        self.tempCtrls_sp_update_btn.setMinimumHeight(24)
        self.magneticStirrers_sp_update_btn = QPushButton("Update Magnetic Stirrer Set Points", evoflow_control_groupbox)
        self.magneticStirrers_sp_update_btn.setStyleSheet(button_style)
        self.magneticStirrers_sp_update_btn.setMinimumHeight(24)
        self.reset_all_slideswitches_btn = QPushButton("Reset All Slide Switches", evoflow_control_groupbox)
        self.reset_all_slideswitches_btn.setStyleSheet(button_style)
        self.reset_all_slideswitches_btn.setMinimumHeight(24)

        evoflow_control_V_layout.addWidget(self.pumps_sp_update_btn)
        evoflow_control_V_layout.addWidget(self.tempCtrls_sp_update_btn)
        evoflow_control_V_layout.addWidget(self.magneticStirrers_sp_update_btn)
        evoflow_control_V_layout.addWidget(self.reset_all_slideswitches_btn)
        evoflow_control_V_layout.addStretch()  # Push the buttons to the top


        controller_status_groupbox = QGroupBox("Controllers Status", self)
        controller_status_groupbox.setStyleSheet(groupbox_style)
        controller_status_groupbox.setGeometry(1505, 290, 250, 150)
        controller_status_V_layout = QVBoxLayout(controller_status_groupbox)

        controller_status_first_row_layout = QHBoxLayout()
        controller_status_second_row_layout = QHBoxLayout()
        controller_status_third_row_layout = QHBoxLayout()
        controller_status_forth_row_layout = QHBoxLayout()
        controller_status_fifth_row_layout = QHBoxLayout()

        evoflow_status_label = QLabel("Evoflow Status:", controller_status_groupbox)
        evoflow_status_label.setStyleSheet(font_small_value)
        se_status_label = QLabel("SE Status:", controller_status_groupbox)
        se_status_label.setStyleSheet(font_small_value)
        self.led_evoflow_status = QLabel("⚪", controller_status_groupbox)  #🔴🟢
        self.led_se_status = QLabel("⚪", controller_status_groupbox)  #🔴🟢
        evoflow_comm_label = QLabel("Evoflow Comm.:", controller_status_groupbox)
        evoflow_comm_label.setStyleSheet(font_small_value)
        self.led_evoflow_comm = QLabel("⚪", controller_status_groupbox)  #🔴🟢
        self.reset_evoflow_btn = QPushButton("Reset Evoflow", controller_status_groupbox)
        self.reset_evoflow_btn.setStyleSheet(button_style)
        self.reset_se_btn = QPushButton("Reset SE", controller_status_groupbox)
        self.reset_se_btn.setStyleSheet(button_style)
        rpi_temp_label = QLabel("RPI Temp: ", controller_status_groupbox)
        rpi_temp_label.setStyleSheet(font_small_value)
        self.rpi_temp_label = QLabel("0 °C", controller_status_groupbox)
        self.rpi_temp_label.setStyleSheet(font_small_value)
        evoflow_temp_label = QLabel("EvoFlow Temp:", controller_status_groupbox)
        evoflow_temp_label.setStyleSheet(font_small_value)
        self.evoflow_temp_label = QLabel("0 °C", controller_status_groupbox)
        self.evoflow_temp_label.setStyleSheet(font_small_value)
        no_of_evoflow_reset_label = QLabel("No. of Evoflow Resets:", controller_status_groupbox)
        no_of_evoflow_reset_label.setStyleSheet(font_small_value)
        self.no_of_evoflow_reset_label = QLabel("0", controller_status_groupbox)
        self.no_of_evoflow_reset_label.setStyleSheet(font_small_value)

        controller_status_first_row_layout.addWidget(evoflow_status_label)
        controller_status_first_row_layout.addWidget(self.led_evoflow_status)
        controller_status_first_row_layout.addWidget(se_status_label)
        controller_status_first_row_layout.addWidget(self.led_se_status)
        controller_status_second_row_layout.addWidget(evoflow_comm_label)
        controller_status_second_row_layout.addWidget(self.led_evoflow_comm)
        controller_status_second_row_layout.addStretch()
        controller_status_third_row_layout.addWidget(self.reset_evoflow_btn)
        controller_status_third_row_layout.addWidget(self.reset_se_btn)
        controller_status_forth_row_layout.addWidget(rpi_temp_label)
        controller_status_forth_row_layout.addWidget(self.rpi_temp_label)
        controller_status_forth_row_layout.addWidget(evoflow_temp_label)
        controller_status_forth_row_layout.addWidget(self.evoflow_temp_label)
        controller_status_fifth_row_layout.addWidget(no_of_evoflow_reset_label)
        controller_status_fifth_row_layout.addWidget(self.no_of_evoflow_reset_label)

        controller_status_V_layout.addLayout(controller_status_first_row_layout)
        controller_status_V_layout.addLayout(controller_status_second_row_layout)
        controller_status_V_layout.addLayout(controller_status_third_row_layout)
        controller_status_V_layout.addLayout(controller_status_forth_row_layout)
        controller_status_V_layout.addLayout(controller_status_fifth_row_layout)


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

        self.pump_1_sp_edit = QLineEdit(self)
        self.pump_1_sp_edit.setText(str(self.default_pump_1))
        self.pump_1_sp_edit.setGeometry(116, 302, 45, 20)
        self.pump_1_sp_edit.setStyleSheet(edit_style)
        self.pump_1_feedback = QLabel("FB: 0 rpm\n0 rpm, 0 ul/min", self)
        self.pump_1_feedback.setGeometry(29, 322, 170, 30)
        self.pump_1_feedback.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self.pump_1_feedback.setStyleSheet(font_small_value)

        self.pump_2_sp_edit = QLineEdit(self)
        self.pump_2_sp_edit.setText(str(self.default_pump_2))
        self.pump_2_sp_edit.setGeometry(676, 302, 45, 20)
        self.pump_2_sp_edit.setStyleSheet(edit_style)
        self.pump_2_feedback = QLabel("FB: 0 rpm\n0 rpm, 0 ul/min", self)
        self.pump_2_feedback.setGeometry(592, 322, 170, 30)
        self.pump_2_feedback.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self.pump_2_feedback.setStyleSheet(font_small_value)

        self.pump_3_sp_edit = QLineEdit(self)
        self.pump_3_sp_edit.setText(str(self.default_pump_3))
        self.pump_3_sp_edit.setGeometry(1149, 323, 45, 20)
        self.pump_3_sp_edit.setStyleSheet(edit_style)
        self.pump_3_feedback = QLabel("FB: 0 rpm\n0 rpm, 0 ul/min", self)
        self.pump_3_feedback.setGeometry(1062, 343, 170, 30)
        self.pump_3_feedback.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self.pump_3_feedback.setStyleSheet(font_small_value)

        self.pump_4_sp_edit = QLineEdit(self)
        self.pump_4_sp_edit.setText(str(self.default_pump_4))
        self.pump_4_sp_edit.setGeometry(1149, 157, 45, 20)
        self.pump_4_sp_edit.setStyleSheet(edit_style)
        self.pump_4_feedback = QLabel("FB: 0 rpm\n0 rpm, 0 ul/min", self)
        self.pump_4_feedback.setGeometry(1062, 177, 170, 30)
        self.pump_4_feedback.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self.pump_4_feedback.setStyleSheet(font_small_value)

        self.magneticStirrer_bioreactor_sp_edit = QLineEdit(self)
        self.magneticStirrer_bioreactor_sp_edit.setText(str(self.default_magneticStirrer_bioreactor))
        self.magneticStirrer_bioreactor_sp_edit.setGeometry(290, 326, 50, 20)
        self.magneticStirrer_bioreactor_sp_edit.setStyleSheet(edit_style)
        self.magneticStirrer_bioreactor_feedback = QLabel("FB: 0 rpm\n0 rpm, 0.0 %", self)
        self.magneticStirrer_bioreactor_feedback.setGeometry(203, 347, 170, 30)
        self.magneticStirrer_bioreactor_feedback.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self.magneticStirrer_bioreactor_feedback.setStyleSheet(font_small_value)

        self.magneticStirrer_lagoon_sp_edit = QLineEdit(self)
        self.magneticStirrer_lagoon_sp_edit.setText(str(self.default_magneticStirrer_lagoon))
        self.magneticStirrer_lagoon_sp_edit.setGeometry(817, 326, 50, 20)
        self.magneticStirrer_lagoon_sp_edit.setStyleSheet(edit_style)
        self.magneticStirrer_lagoon_feedback = QLabel("FB: 0 rpm\n0 rpm, 0.0 %", self)
        self.magneticStirrer_lagoon_feedback.setGeometry(730, 347, 170, 30)
        self.magneticStirrer_lagoon_feedback.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
        self.magneticStirrer_lagoon_feedback.setStyleSheet(font_small_value)

        self.tempCtrl_bioreactor_feedback = QLabel("0.0 °C", self)
        self.tempCtrl_bioreactor_feedback.setGeometry(237, 178, 100, 20)
        self.tempCtrl_bioreactor_feedback.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self.tempCtrl_bioreactor_feedback.setStyleSheet(font_value_2)
        self.tempCtrl_bioreactor_sp_edit = QLineEdit(self)
        self.tempCtrl_bioreactor_sp_edit.setText(str(self.default_temp_ctrl_bioreactor))
        self.tempCtrl_bioreactor_sp_edit.setGeometry(401, 196, 50, 20)
        self.tempCtrl_bioreactor_sp_edit.setStyleSheet(edit_style)
        self.tempCtrl_bioreactor_feedback_sp_htr = QLabel("FB: 0.0 °C, Duty: 0.0 %", self)
        self.tempCtrl_bioreactor_feedback_sp_htr.setGeometry(354, 215, 170, 20)
        self.tempCtrl_bioreactor_feedback_sp_htr.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.tempCtrl_bioreactor_feedback_sp_htr.setStyleSheet(font_small_value)

        self.tempCtrl_lagoon_feedback = QLabel("0.0 °C", self)
        self.tempCtrl_lagoon_feedback.setGeometry(764, 178, 100, 20)
        self.tempCtrl_lagoon_feedback.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self.tempCtrl_lagoon_feedback.setStyleSheet(font_value_2)
        self.tempCtrl_lagoon_sp_edit = QLineEdit(self)
        self.tempCtrl_lagoon_sp_edit.setText(str(self.default_temp_ctrl_lagoon))
        self.tempCtrl_lagoon_sp_edit.setGeometry(928, 196, 50, 20)
        self.tempCtrl_lagoon_sp_edit.setStyleSheet(edit_style)
        self.tempCtrl_lagoon_feedback_sp_htr = QLabel("FB: 0.0 °C, Duty: 0.0 %", self)
        self.tempCtrl_lagoon_feedback_sp_htr.setGeometry(881, 215, 170, 20)
        self.tempCtrl_lagoon_feedback_sp_htr.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.tempCtrl_lagoon_feedback_sp_htr.setStyleSheet(font_small_value)

        self.od_bioreactor_feedback = QLabel("0.00", self)
        self.od_bioreactor_feedback.setGeometry(237, 228, 100, 25)
        self.od_bioreactor_feedback.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self.od_bioreactor_feedback.setStyleSheet(font_value_2)
        self.od_lagoon_feedback = QLabel("0.00", self)
        self.od_lagoon_feedback.setGeometry(764, 228, 100, 25)
        self.od_lagoon_feedback.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self.od_lagoon_feedback.setStyleSheet(font_value_2)

        self.phtCount_feedback = QLabel("0.00 MHz", self)
        self.phtCount_feedback.setGeometry(764, 128, 100, 25)
        self.phtCount_feedback.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self.phtCount_feedback.setStyleSheet(font_value_2)

        
        # Testing
        if magneticStirrer_swapping_mode_enabled:
            self.magneticStirrer_bioreactor_swapping_mode_slide_switch = TapSwitch(self)
            self.magneticStirrer_bioreactor_swapping_mode_slide_switch.setGeometry(400, 285, 40, 20)
            self.magneticStirrer_lagoon_swapping_mode_slide_switch = TapSwitch(self)
            self.magneticStirrer_lagoon_swapping_mode_slide_switch.setGeometry(927, 285, 40, 20)

            magneticStirrer_bioreactor_swapping_mode_label = QLabel("Swapping Mode", self)
            magneticStirrer_bioreactor_swapping_mode_label.setGeometry(375, 305, 100, 20)
            magneticStirrer_bioreactor_swapping_mode_label.setStyleSheet(font_component)
            magneticStirrer_lagoon_swapping_mode_label = QLabel("Swapping Mode", self)
            magneticStirrer_lagoon_swapping_mode_label.setGeometry(902, 305, 100, 20)
            magneticStirrer_lagoon_swapping_mode_label.setStyleSheet(font_component)

            magneticStirrer_bioreactor_duration_label = QLabel("Duration(s):", self)
            magneticStirrer_bioreactor_duration_label.setGeometry(375, 325, 100, 20)
            magneticStirrer_bioreactor_duration_label.setStyleSheet(font_small_value)
            self.magneticStirrer_bioreactor_duration_edit = QLineEdit(self)
            self.magneticStirrer_bioreactor_duration_edit.setText("3600")
            self.magneticStirrer_bioreactor_duration_edit.setGeometry(440, 325, 50, 20)
            self.magneticStirrer_bioreactor_duration_edit.setStyleSheet(edit_style)
            magneticStirrer_lagoon_duration_label = QLabel("Duration(s):", self)
            magneticStirrer_lagoon_duration_label.setGeometry(902, 325, 100, 20)
            magneticStirrer_lagoon_duration_label.setStyleSheet(font_small_value)
            self.magneticStirrer_lagoon_duration_edit = QLineEdit(self)
            self.magneticStirrer_lagoon_duration_edit.setText("3600")
            self.magneticStirrer_lagoon_duration_edit.setGeometry(967, 325, 50, 20)
            self.magneticStirrer_lagoon_duration_edit.setStyleSheet(edit_style)

            self.magneticStirrer_bioreactor_duration = 0
            self.magneticStirrer_lagoon_duration = 0

            self.magneticStirrer_bioreactor_swapping_mode_status = False
            self.magneticStirrer_lagoon_swapping_mode_status = False

            # Timers for swapping mode
            self.magneticStirrer_bioreactor_swapping_mode_timer = QTimer(self)
            self.magneticStirrer_lagoon_swapping_mode_timer = QTimer(self)
            self.magneticStirrer_bioreactor_swapping_mode_timer.timeout.connect(self.handle_magneticStirrer_bioreactor_swapping_mode_timeout)
            self.magneticStirrer_lagoon_swapping_mode_timer.timeout.connect(self.handle_magneticStirrer_lagoon_swapping_mode_timeout)

    def connect_signals(self):
        """Connect signals to their respective slots"""
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

        # Combined button design
        self.pumps_sp_update_btn.clicked.connect(self.handle_pump_sp_update)
        self.magneticStirrers_sp_update_btn.clicked.connect(self.handle_magneticStirrer_sp_update)
        self.tempCtrls_sp_update_btn.clicked.connect(self.handle_tempCtrl_sp_update)

        self.reset_all_slideswitches_btn.clicked.connect(self.handle_reset_all_slideswitches)

        self.reset_evoflow_btn.clicked.connect(self.reset_evoflow_requested)

        # Pressing enter in the setpoint edits should also trigger the update
        self.pump_1_sp_edit.returnPressed.connect(self.handle_pump_sp_update)
        self.pump_2_sp_edit.returnPressed.connect(self.handle_pump_sp_update)
        self.pump_3_sp_edit.returnPressed.connect(self.handle_pump_sp_update)
        self.pump_4_sp_edit.returnPressed.connect(self.handle_pump_sp_update)
        self.magneticStirrer_bioreactor_sp_edit.returnPressed.connect(self.handle_magneticStirrer_sp_update)
        self.magneticStirrer_lagoon_sp_edit.returnPressed.connect(self.handle_magneticStirrer_sp_update)
        self.tempCtrl_bioreactor_sp_edit.returnPressed.connect(self.handle_tempCtrl_sp_update)
        self.tempCtrl_lagoon_sp_edit.returnPressed.connect(self.handle_tempCtrl_sp_update)

        if magneticStirrer_swapping_mode_enabled:
            self.magneticStirrer_bioreactor_swapping_mode_slide_switch.toggled.connect(self.handle_magneticStirrer_bioreactor_swapping_mode_toggle)
            self.magneticStirrer_lagoon_swapping_mode_slide_switch.toggled.connect(self.handle_magneticStirrer_lagoon_swapping_mode_toggle)

        
    def load_default_config(self):
        """Load flow rate conversion factors from config/settings.ini"""
        config = self.read_settings_file()
        self.default_pump_1 = config.getfloat("defaultValues", "pump1_flow")
        self.default_pump_2 = config.getfloat("defaultValues", "pump2_flow")
        self.default_pump_3 = config.getfloat("defaultValues", "pump3_flow")
        self.default_pump_4 = config.getfloat("defaultValues", "pump4_flow")
        self.default_temp_ctrl_bioreactor = config.getfloat("defaultValues", "tempCtrl_bioreactor_sp")
        self.default_temp_ctrl_lagoon = config.getfloat("defaultValues", "tempCtrl_lagoon_sp")
        self.default_magneticStirrer_bioreactor = config.getfloat("defaultValues", "magneticStirrer_bioreactor_rpm")
        self.default_magneticStirrer_lagoon = config.getfloat("defaultValues", "magneticStirrer_lagoon_rpm")
        self._flow_rate_pump_1_list, self._flow_rate_pump_2_list, self._flow_rate_pump_3_list, self._flow_rate_pump_4_list = self.extract_flow_conversion_factors(
            config.get("flowRateConversionFactors", "pump_1"),
            config.get("flowRateConversionFactors", "pump_2"),
            config.get("flowRateConversionFactors", "pump_3"),
            config.get("flowRateConversionFactors", "pump_4"),
        )

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
        # check if both valves are off, turn off the pump no 2 as well to prevent creating vacuum in the system
        if not valve_bio2lag_status and not valve_sug2lag_status:
            self.slide_switch_pump_2.setChecked(False)
            self.handle_pump_toggle(False)

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
            rpm_1 = self.ul_per_min_to_rpm(1, new_sp_1)
            rpm_2 = self.ul_per_min_to_rpm(2, new_sp_2)
            rpm_3 = self.ul_per_min_to_rpm(3, new_sp_3)
            rpm_4 = self.ul_per_min_to_rpm(4, new_sp_4)
            self.pump_sp_update_requested.emit(rpm_1, rpm_2, rpm_3, rpm_4)
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

    def handle_reset_all_slideswitches(self):
        """Reset all slide switches to off position (for development/testing purposes)"""
        self.slide_switch_pump_1.setChecked(False)
        self.slide_switch_pump_2.setChecked(False)
        self.slide_switch_pump_3.setChecked(False)
        self.slide_switch_pump_4.setChecked(False)
        self.slide_switch_magneticStirrer_bioreactor.setChecked(False)
        self.slide_switch_magneticStirrer_lagoon.setChecked(False)
        self.slide_switch_od_bioreactor.setChecked(False)
        self.slide_switch_od_lagoon.setChecked(False)
        self.slide_switch_tempCtrl_bioreactor.setChecked(False)
        self.slide_switch_tempCtrl_lagoon.setChecked(False)
        self.slide_switch_valve_bio2lag.setChecked(False)
        self.slide_switch_valve_sug2lag.setChecked(False)
        self.slide_switch_phtCount_Lagoon.setChecked(False)

    def handle_magneticStirrer_bioreactor_swapping_mode_toggle(self, checked):
        """Handle magnetic stirrer bioreactor swapping mode toggle"""
        duration = int(self.magneticStirrer_bioreactor_duration_edit.text())
        if checked:
            self.magneticStirrer_bioreactor_swapping_mode_timer.start(duration * 1000)  # Convert seconds to milliseconds
            self.magneticStirrer_bioreactor_swapping_mode_status = True
        else:
            self.magneticStirrer_bioreactor_swapping_mode_timer.stop()
            self.magneticStirrer_bioreactor_swapping_mode_status = False

    def handle_magneticStirrer_lagoon_swapping_mode_toggle(self, checked):
        """Handle magnetic stirrer lagoon swapping mode toggle"""
        duration = int(self.magneticStirrer_lagoon_duration_edit.text())
        if checked:
            self.magneticStirrer_lagoon_swapping_mode_timer.start(duration * 1000)  # Convert seconds to milliseconds
            self.magneticStirrer_lagoon_swapping_mode_status = True
        else:
            self.magneticStirrer_lagoon_swapping_mode_timer.stop()
            self.magneticStirrer_lagoon_swapping_mode_status = False

    def handle_magneticStirrer_bioreactor_swapping_mode_timeout(self):
        """Handle timeout for magnetic stirrer bioreactor swapping mode"""
        magneticStirrer_bioreactor_status = self.slide_switch_magneticStirrer_bioreactor.isChecked()
        self.slide_switch_magneticStirrer_bioreactor.setChecked(not magneticStirrer_bioreactor_status)

    def handle_magneticStirrer_lagoon_swapping_mode_timeout(self):
        """Handle timeout for magnetic stirrer lagoon swapping mode"""
        magneticStirrer_lagoon_status = self.slide_switch_magneticStirrer_lagoon.isChecked()
        self.slide_switch_magneticStirrer_lagoon.setChecked(not magneticStirrer_lagoon_status)

    @Slot(EvoFlowTelemetry)
    def update_telemetry(self, evoflow_telemetry):
        """Update the widget based on incoming telemetry"""

        # New design with checks if telemetry is not the same as the current displayed values,
        # we then send commands to update Necleo to have to same values as the slide switches.
        # GUI is the master and Necleo is the slave, so if there is a mismatch, we update Necleo to match the GUI (slide switch states).

        pump_status_mismatch = (
            evoflow_telemetry.pump_1_status != self.slide_switch_pump_1.isChecked()
            or evoflow_telemetry.pump_2_status != self.slide_switch_pump_2.isChecked()
            or evoflow_telemetry.pump_3_status != self.slide_switch_pump_3.isChecked()
            or evoflow_telemetry.pump_4_status != self.slide_switch_pump_4.isChecked()
        )
        if pump_status_mismatch:
            self.handle_pump_toggle(False)

        magnetic_stirrer_status_mismatch = (
            evoflow_telemetry.magneticStirrer_bioreactor_status != self.slide_switch_magneticStirrer_bioreactor.isChecked()
            or evoflow_telemetry.magneticStirrer_lagoon_status != self.slide_switch_magneticStirrer_lagoon.isChecked()
        )
        if magnetic_stirrer_status_mismatch:
            self.handle_magneticStirrer_toggle(False)

        temp_ctrl_status_mismatch = (
            evoflow_telemetry.tempCtrl_bioreactor_status != self.slide_switch_tempCtrl_bioreactor.isChecked()
            or evoflow_telemetry.tempCtrl_lagoon_status != self.slide_switch_tempCtrl_lagoon.isChecked()
        )
        if temp_ctrl_status_mismatch:
            self.handle_tempCtrl_toggle(False)

        od_status_mismatch = (
            evoflow_telemetry.od_bioreactor_status != self.slide_switch_od_bioreactor.isChecked()
            or evoflow_telemetry.od_lagoon_status != self.slide_switch_od_lagoon.isChecked()
        )
        if od_status_mismatch:
            self.handle_od_toggle(False)

        if evoflow_telemetry.phtCount_lagoon_status != self.slide_switch_phtCount_Lagoon.isChecked():
            self.handle_phtCount_toggle(False)

        valve_status_mismatch = (
            evoflow_telemetry.valve_bio2lag_status != self.slide_switch_valve_bio2lag.isChecked()
            or evoflow_telemetry.valve_sug2lag_status != self.slide_switch_valve_sug2lag.isChecked()
        )
        if valve_status_mismatch:
            self.handle_valve_toggle(False)

        # pump_sp_mismatch = (
        #     evoflow_telemetry.pump_1_sp != float(self.pump_1_sp_edit.text())
        #     or evoflow_telemetry.pump_2_sp != float(self.pump_2_sp_edit.text())
        #     or evoflow_telemetry.pump_3_sp != float(self.pump_3_sp_edit.text())
        #     or evoflow_telemetry.pump_4_sp != float(self.pump_4_sp_edit.text())
        # )
        # if pump_sp_mismatch:
        #     self.handle_pump_sp_update()

        # temp_ctrl_sp_mismatch = (
        #     evoflow_telemetry.tempCtrl_bioreactor_sp != float(self.tempCtrl_bioreactor_sp_edit.text())
        #     or evoflow_telemetry.tempCtrl_lagoon_sp != float(self.tempCtrl_lagoon_sp_edit.text())
        # )
        # if temp_ctrl_sp_mismatch:
        #     self.handle_tempCtrl_sp_update()
        
        # magnetic_stirrer_sp_mismatch = (
        #     evoflow_telemetry.magneticStirrer_bioreactor_sp != float(self.magneticStirrer_bioreactor_sp_edit.text())
        #     or evoflow_telemetry.magneticStirrer_lagoon_sp != float(self.magneticStirrer_lagoon_sp_edit.text())
        # )
        # if magnetic_stirrer_sp_mismatch:
        #     self.handle_magneticStirrer_sp_update()


        # Update pump 1
        if evoflow_telemetry.pump_1_status:
            self.led_pump_1.setText("🟢")
        else:
            self.led_pump_1.setText("🔴")
        self.pump_1_feedback.setText(f"FB: {evoflow_telemetry.pump_1_sp:.2f} rpm\n{evoflow_telemetry.pump_1_speed:.2f} rpm, {(self.rpm_to_ul_per_min(1, evoflow_telemetry.pump_1_speed)):.0f} ul/min")
        # Update pump 2
        if evoflow_telemetry.pump_2_status:
            self.led_pump_2.setText("🟢")
        else:
            self.led_pump_2.setText("🔴")
        self.pump_2_feedback.setText(f"FB: {evoflow_telemetry.pump_2_sp:.2f} rpm\n{evoflow_telemetry.pump_2_speed:.2f} rpm, {(self.rpm_to_ul_per_min(2, evoflow_telemetry.pump_2_speed)):.0f} ul/min")
        # Update pump 3
        if evoflow_telemetry.pump_3_status:
            self.led_pump_3.setText("🟢")
        else:
            self.led_pump_3.setText("🔴")
        self.pump_3_feedback.setText(f"FB: {evoflow_telemetry.pump_3_sp:.2f} rpm\n{evoflow_telemetry.pump_3_speed:.2f} rpm, {(self.rpm_to_ul_per_min(3, evoflow_telemetry.pump_3_speed)):.0f} ul/min")
        # Update pump 4
        if evoflow_telemetry.pump_4_status:
            self.led_pump_4.setText("🟢")
        else:
            self.led_pump_4.setText("🔴")
        self.pump_4_feedback.setText(f"FB: {evoflow_telemetry.pump_4_sp:.2f} rpm\n{evoflow_telemetry.pump_4_speed:.2f} rpm, {(self.rpm_to_ul_per_min(4, evoflow_telemetry.pump_4_speed)):.0f} ul/min")

        # Update magnetic stirrer bioreactor
        if evoflow_telemetry.magneticStirrer_bioreactor_status:
            self.led_magneticStirrer_bioreactor.setText("🟢")
        else:
            self.led_magneticStirrer_bioreactor.setText("🔴")
        self.magneticStirrer_bioreactor_feedback.setText(f"FB: {evoflow_telemetry.magneticStirrer_bioreactor_sp:.0f} rpm\n{evoflow_telemetry.magneticStirrer_bioreactor_speed:.0f} rpm, {evoflow_telemetry.magneticStirrer_bioreactor_fan_duty_cycle*100:.1f} %")
        # Update magnetic stirrer lagoon
        if evoflow_telemetry.magneticStirrer_lagoon_status:
            self.led_magneticStirrer_lagoon.setText("🟢")
        else:
            self.led_magneticStirrer_lagoon.setText("🔴")
        self.magneticStirrer_lagoon_feedback.setText(f"FB: {evoflow_telemetry.magneticStirrer_lagoon_sp:.0f} rpm\n{evoflow_telemetry.magneticStirrer_lagoon_speed:.0f} rpm, {evoflow_telemetry.magneticStirrer_lagoon_fan_duty_cycle*100:.1f} %")

        # Update temperature controller bioreactor
        if evoflow_telemetry.tempCtrl_bioreactor_status:
            self.led_tempCtrl_bioreactor.setText("🟢")
        else:
            self.led_tempCtrl_bioreactor.setText("🔴")
        self.tempCtrl_bioreactor_feedback.setText(f"{evoflow_telemetry.tempCtrl_bioreactor_value:.1f} °C")
        self.tempCtrl_bioreactor_feedback_sp_htr.setText(f"FB: {evoflow_telemetry.tempCtrl_bioreactor_sp:.1f} °C, Duty: {evoflow_telemetry.tempCtrl_bioreactor_heater_duty_cycle*100:.1f} %")
        # Update temperature controller lagoon
        if evoflow_telemetry.tempCtrl_lagoon_status:
            self.led_tempCtrl_lagoon.setText("🟢")
        else:
            self.led_tempCtrl_lagoon.setText("🔴")
        self.tempCtrl_lagoon_feedback.setText(f"{evoflow_telemetry.tempCtrl_lagoon_value:.1f} °C")
        self.tempCtrl_lagoon_feedback_sp_htr.setText(f"FB: {evoflow_telemetry.tempCtrl_lagoon_sp:.1f} °C, Duty: {evoflow_telemetry.tempCtrl_lagoon_heater_duty_cycle*100:.1f} %")

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
        self.phtCount_feedback.setText(f"{evoflow_telemetry.phtCount_lagoon_value:.2f} MHz")
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

        # Update nucleo temperature
        self.evoflow_temp_label.setText(f"{evoflow_telemetry.nucleo_temperature:.0f} °C")

    @Slot(bool)
    def update_evoflow_status(self, evoflow_status):
        """Update Evoflow status LED"""
        if evoflow_status:
            self.led_evoflow_status.setText("🟢")
        else:
            self.led_evoflow_status.setText("🔴")

    @Slot(bool)
    def update_evoflow_comm_status(self, evoflow_comm_status):
        """Update Evoflow communication status LED"""
        self.led_evoflow_comm.setText("🔵" if evoflow_comm_status else "🔴")

        # Reuse one timer to avoid creating unbounded timer objects during long runs.
        self._evoflow_comm_led_reset_timer.start(self._evoflow_comm_led_hold_ms)

    @Slot()
    def _reset_evoflow_comm_led(self):
        self.led_evoflow_comm.setText("⚪")

    @Slot(int)
    def update_rpi_temp(self, rpi_temp):
        """Update Raspberry Pi temperature label"""
        self.rpi_temp_label.setText(f"{rpi_temp:.0f} °C")

    @Slot(int)
    def update_no_of_evoflow_reset(self, no_of_evoflow_reset):
        """Update the number of Evoflow resets label"""
        self.no_of_evoflow_reset_label.setText(f"{no_of_evoflow_reset}")

    def extract_flow_conversion_factors(self, pump1_str_list: str, pump2_str_list: str, pump3_str_list: str, pump4_str_list: str) -> tuple[list[float], list[float], list[float], list[float]]:
        """Extract flow conversion factors from string lists and store them as floats"""
        try:
            pump1_factors = [float(x) for x in pump1_str_list.split(",") if x.strip()]
            pump2_factors = [float(x) for x in pump2_str_list.split(",") if x.strip()]
            pump3_factors = [float(x) for x in pump3_str_list.split(",") if x.strip()]
            pump4_factors = [float(x) for x in pump4_str_list.split(",") if x.strip()]

            return pump1_factors, pump2_factors, pump3_factors, pump4_factors
        except ValueError as e:
            self.status_message.emit(f"Error parsing flow conversion factors: {e}")
            return [], [], [], []
        
    def rpm_to_ul_per_min(self, pump_number: int, rpm: float) -> float:
        """Convert RPM to ul/min using polynomial fit for the specified pump"""
        if pump_number == 1:
            # Use second order polynomial fit for pump 1
            flow = self._flow_rate_pump_1_list[0]*rpm**2 + self._flow_rate_pump_1_list[1]*rpm + self._flow_rate_pump_1_list[2]
            return flow
        elif pump_number == 2:
            # Use second order polynomial fit for pump 2
            flow = self._flow_rate_pump_2_list[0]*rpm**2 + self._flow_rate_pump_2_list[1]*rpm + self._flow_rate_pump_2_list[2]
            return flow
        elif pump_number == 3:
            # Use second order polynomial fit for pump 3
            flow = self._flow_rate_pump_3_list[0]*rpm**2 + self._flow_rate_pump_3_list[1]*rpm + self._flow_rate_pump_3_list[2]
            return flow
        elif pump_number == 4:
            # Use second order polynomial fit for pump 4
            flow = self._flow_rate_pump_4_list[0]*rpm**2 + self._flow_rate_pump_4_list[1]*rpm + self._flow_rate_pump_4_list[2]
            return flow
        else:
            raise ValueError("Invalid pump number. Must be 1, 2, 3, or 4.")
        
    def ul_per_min_to_rpm(self, pump_number: int, ul_per_min: float) -> float:
        """Convert uL/min to RPM using polynomial fit for the specified pump"""
        if ul_per_min == 0:
            return 0.0

        flow_magnitude = abs(ul_per_min)

        if pump_number == 1:
            # Use second order polynomial fit for pump 1
            a, b, c = self._flow_rate_pump_1_list
        elif pump_number == 2:
            # Use second order polynomial fit for pump 2
            a, b, c = self._flow_rate_pump_2_list
        elif pump_number == 3:
            # Use second order polynomial fit for pump 3
            a, b, c = self._flow_rate_pump_3_list
        elif pump_number == 4:
            # Use second order polynomial fit for pump 4
            a, b, c = self._flow_rate_pump_4_list
        else:
            raise ValueError("Invalid pump number. Must be 1, 2, 3, or 4.")

        # Use the fitted forward-direction curve to get RPM magnitude, then apply the requested flow sign.
        coeffs = [a, b, c - flow_magnitude]
        roots = np.roots(coeffs)
        real_roots = roots[np.isreal(roots)].real

        if len(real_roots) == 0:
            raise ValueError("No real solution found for the given uL/min value.")

        # Keep only physically valid positive RPM magnitudes; reverse direction is applied afterward.
        rpm_abs_max = 600.0
        valid_roots = real_roots[(real_roots >= 0.0) & (real_roots <= rpm_abs_max)]

        if len(valid_roots) == 0:
            raise ValueError(
                f"No valid RPM magnitude solution in [0.0, {rpm_abs_max}] for pump {pump_number} and flow {ul_per_min} uL/min."
            )

        rpm_magnitude = float(valid_roots[np.argmin(np.abs(valid_roots))])
        return rpm_magnitude if ul_per_min > 0 else -rpm_magnitude

    def read_settings_file(self):
        """Load default configuration values from settings.ini"""
        # config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'settings.ini')      # for development
        config_path = resource_path("config/settings.ini")       # for bundling with PyInstaller
        config = configparser.ConfigParser()
        config.read(str(config_path))
        return config

