# EvoFlow HMI Architecture

Complete communication framework for EvoFlow bioreactor and Pick&Place machine control, following MVC pattern with PySide6.

## Project Structure

```
evoflow_control_entity/
├── evoflow/                          # Low-level device communication
│   └── device/
│       ├── __init__.py
│       ├── communication.py         # Protocol primitives (COBS, CRC16, packet building)
│       ├── evoflow_device.py        # EvoFlow device class (serial I/O + state)
│       └── pickplace_device.py      # Pick&Place device class
│
├── controlEntity/                   # Application logic and UI
│   ├── __init__.py
│   ├── main.py                      # Entry point
│   │
│   ├── logic/                       # Worker threads and coordinators
│   │   ├── __init__.py
│   │   ├── logic.py                 # Main logic coordinator (wires everything)
│   │   ├── evoflow_worker.py        # EvoFlow Qt worker (runs in thread)
│   │   └── pickplace_worker.py      # Pick&Place Qt worker
│   │
│   └── pages/                       # HMI views (TODO: create your tabs here)
│       ├── main_ui.py
│       └── evoflow_tab.py
```

## Architecture Pattern

### **Layer 1: Low-Level Device Classes** (`evoflow/device/`)

**Purpose:** Pure communication, no Qt dependencies, thread-safe with locks.

- `communication.py`: Protocol building blocks
  - COBS encoding/decoding
  - CRC16 calculation
  - Packet building/parsing
  - Stream parser

- `evoflow_device.py`: EvoFlow-specific communication
  - Serial port management
  - Setpoint storage (vel, temp, stir)
  - Telemetry parsing
  - Bootstrap logic

- `pickplace_device.py`: Pick&Place communication
  - Supports two protocols: FULL (COBS+CRC) or SIMPLE (strings)
  - Move/gripper/home commands

### **Layer 2: Worker Classes** (`controlEntity/logic/`)

**Purpose:** Qt workers that run in threads, emit signals to HMI.

- `evoflow_worker.py`:
  - Creates `EvoFlowDevice` instance
  - Runs RX loop at 100 Hz (reads telemetry)
  - Runs TX loop at 20 Hz (sends setpoints)
  - Emits Qt signals for telemetry and results

- `pickplace_worker.py`:
  - Creates `PickPlaceDevice` instance
  - Handles commands on-demand
  - Emits results via signals

### **Layer 3: Logic Coordinator** (`controlEntity/logic/logic.py`)

**Purpose:** Wire workers to UI, manage thread lifecycle.

- Creates `QThread` for each worker
- Moves workers to threads
- Connects UI signals → worker slots
- Connects worker signals → UI updates
- Maintains connection state

### **Layer 4: HMI** (`controlEntity/pages/`)

**Purpose:** PySide6 UI components.

- Creates logic instance
- Connects buttons/sliders to logic signals
- Receives telemetry updates
- Updates displays

## Communication Protocol

### **EvoFlow Protocol (Binary)**

**Packet Structure:**
```
[msg_id][node_id][payload_len][payload...][crc16_le]
    ↓
COBS encode → append 0x00 delimiter → transmit
```

**Message Types:**
- `0x01` MSG_TELEM: Telemetry (100 Hz from MCU)
- `0x10` MSG_CMD_SET: Setpoints (20 Hz to MCU)
- `0x11` MSG_ACK_CMD_SET: ACK from MCU
- `0x20` MSG_CMD_ACTION: Start/Stop
- `0x21` MSG_ACK_ACTION: Action ACK

**Telemetry Payload (64 bytes):**
```python
uptime_s (uint32) + 15 floats:
  0. dtime_us
  1. vel_target_m1
  2. vel_target_m2
  3. vel_m1 (actual)
  4. vel_m2 (actual)
  5. heater_cur_m1
  6. heater_cur_m2
  7. temp_filt_m1
  8. temp_filt_m2
  9. cmd_vel_m1 (echo)
 10. cmd_vel_m2 (echo)
 11. cmd_temp_m1 (echo)
 12. cmd_temp_m2 (echo)
 13. cmd_stir_m1 (echo)
 14. cmd_stir_m2 (echo)
```

**CMD_SET Payload (25 bytes):**
```python
seq (uint8) + 6 floats:
  vel_m1, vel_m2, temp_m1, temp_m2, stir_m1, stir_m2
```

### **Pick&Place Protocol**

#### **Option 1: SIMPLE (String-Based)**
```python
# Commands:
"MOVE 10.5 20.3 5.0\n"
"GRIP OPEN\n"
"GRIP CLOSE\n"
"HOME\n"

# Responses:
"OK\n"
"ERROR: ...\n"
```

#### **Option 2: FULL (Same as EvoFlow)**
Uses COBS+CRC with different message IDs:
- `0x30` MSG_PP_MOVE
- `0x31` MSG_PP_GRIPPER

## Usage Examples

### **Example 1: Basic HMI Tab**

```python
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QSlider, QLabel
from PySide6.QtCore import Slot

class EvoFlowTab(QWidget):
    def __init__(self, logic, parent=None):
        super().__init__(parent)
        self.logic = logic
        self.init_ui()
        self.connect_signals()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Connect button
        self.connect_btn = QPushButton("Connect EvoFlow")
        self.connect_btn.clicked.connect(self.on_connect_clicked)
        layout.addWidget(self.connect_btn)
        
        # Temperature slider
        self.temp_label = QLabel("Temperature 1: 32.0 °C")
        layout.addWidget(self.temp_label)
        
        self.temp_slider = QSlider()
        self.temp_slider.setMinimum(20)
        self.temp_slider.setMaximum(50)
        self.temp_slider.setValue(32)
        self.temp_slider.setOrientation(Qt.Horizontal)
        self.temp_slider.valueChanged.connect(self.on_temp_changed)
        layout.addWidget(self.temp_slider)
        
        # Temperature display
        self.temp_display = QLabel("Actual: -- °C")
        layout.addWidget(self.temp_display)
        
        # Start button
        self.start_btn = QPushButton("START")
        self.start_btn.clicked.connect(lambda: self.logic.evoflow_start_requested.emit())
        layout.addWidget(self.start_btn)
        
        self.setLayout(layout)
    
    def connect_signals(self):
        # Receive telemetry updates
        self.logic.evoflow_telemetry.connect(self.on_telemetry)
        
        # Receive connection results
        self.logic.evoflow_command_result.connect(self.on_command_result)
    
    def on_connect_clicked(self):
        port = "/dev/ttyUSB0"  # Or from a combobox
        node_id = 1
        self.logic.evoflow_connect_requested.emit(port, node_id)
    
    def on_temp_changed(self, value):
        self.temp_label.setText(f"Temperature 1: {value} °C")
        self.logic.evoflow_set_temperature_requested.emit(1, float(value))
    
    @Slot(object)
    def on_telemetry(self, telem):
        """Update display with real-time telemetry."""
        self.temp_display.setText(f"Actual: {telem.temp_filt_m1:.2f} °C")
    
    @Slot(str, object)
    def on_command_result(self, command, payload):
        if command == 'connect':
            success = payload['result'].success
            self.connect_btn.setText("Disconnect" if success else "Connect")
```

### **Example 2: Programmatic Control**

```python
from controlEntity.logic import Logic

# Create logic
logic = Logic()

# Connect to EvoFlow
logic.evoflow_connect_requested.emit("/dev/ttyUSB0", 1)

# Wait for bootstrap (or use signal)
import time
time.sleep(1)

# Set temperature
logic.evoflow_set_temperature_requested.emit(1, 37.0)

# Set pump velocity
logic.evoflow_set_velocity_requested.emit(1, 2.5)

# Start system
logic.evoflow_start_requested.emit()

# Monitor telemetry
def on_telem(telem):
    print(f"Temp: {telem.temp_filt_m1:.2f} °C, Vel: {telem.vel_m1:.2f} rps")

logic.evoflow_telemetry.connect(on_telem)
```

### **Example 3: Pick&Place Control**

```python
# Connect to Pick&Place
logic.pickplace_connect_requested.emit("COM5")

# Move to position
logic.pickplace_move_requested.emit(10.5, 20.3, 5.0)

# Open gripper
logic.pickplace_gripper_requested.emit(True)

# Home
logic.pickplace_home_requested.emit()
```

## Signal Reference

### **EvoFlow Signals**

**From UI to Logic (Commands):**
- `evoflow_connect_requested(port: str, node_id: int)`
- `evoflow_disconnect_requested()`
- `evoflow_set_velocity_requested(pump_id: int, velocity: float)`
- `evoflow_set_temperature_requested(heater_id: int, temp: float)`
- `evoflow_set_stirrer_requested(stir_id: int, voltage: float)`
- `evoflow_start_requested()`
- `evoflow_stop_requested()`

**From Logic to UI (Updates):**
- `evoflow_telemetry(telem: EvoFlowTelemetry)` - 100 Hz updates
- `evoflow_command_result(command: str, payload: dict)`
- `evoflow_status(message: str)`
- `evoflow_error(message: str)`

### **Pick&Place Signals**

**From UI to Logic:**
- `pickplace_connect_requested(port: str)`
- `pickplace_disconnect_requested()`
- `pickplace_move_requested(x: float, y: float, z: float)`
- `pickplace_gripper_requested(open: bool)`
- `pickplace_home_requested()`

**From Logic to UI:**
- `pickplace_command_result(command: str, payload: dict)`
- `pickplace_status(message: str)`
- `pickplace_error(message: str)`

## Development Workflow

1. **Test low-level devices:**
   ```python
   from evoflow.device import EvoFlowDevice
   
   device = EvoFlowDevice()
   result = device.connect("/dev/ttyUSB0")
   print(result.message)
   
   device.set_temperature(1, 37.0)
   device.send_setpoints()
   
   telem = device.read_telemetry()
   if telem:
       print(f"Temp: {telem.temp_filt_m1}")
   ```

2. **Test workers:**
   ```python
   from PySide6.QtCore import QThread
   from controlEntity.logic import EvoFlowWorker
   
   thread = QThread()
   worker = EvoFlowWorker()
   worker.moveToThread(thread)
   
   worker.telemetry.connect(lambda t: print(f"Temp: {t.temp_filt_m1}"))
   
   thread.started.connect(worker.start)
   thread.start()
   
   worker.connect("/dev/ttyUSB0", 1)
   ```

3. **Build HMI:**
   - Create tabs in `controlEntity/pages/`
   - Connect to logic signals
   - Update displays based on telemetry

## Error Handling

Workers emit error signals for:
- Connection failures
- Communication timeouts
- Invalid data

Connect to error signals to display in HMI:
```python
logic.evoflow_error.connect(lambda msg: print(f"ERROR: {msg}"))
```

## Threading Architecture

```
Main Thread (HMI)
    ↓ creates
Logic
    ↓ creates and manages
QThreads:
    ├─ EvoFlow Thread
    │  └─ EvoFlowWorker (QTimers: RX @ 100Hz, TX @ 20Hz)
    │     └─ EvoFlowDevice (serial I/O)
    │
    └─ Pick&Place Thread
       └─ PickPlaceWorker (on-demand commands)
          └─ PickPlaceDevice (serial I/O)
```

**Thread Safety:**
- Device classes use `threading.Lock` for serial I/O
- Workers run in separate QThreads
- Signals/slots handle cross-thread communication
- HMI never directly calls device methods

## Next Steps

1. ✅ Low-level protocol implementation
2. ✅ Device classes (EvoFlow + Pick&Place)
3. ✅ Worker classes with Qt signals
4. ✅ Logic coordinator
5. ⏳ **TODO:** Create HMI tabs (`main_ui.py`, `evoflow_tab.py`)
6. ⏳ **TODO:** Custom widgets (sliders, displays, status indicators)
7. ⏳ **TODO:** Configuration file handling
8. ⏳ **TODO:** Data logging/CSV export

## Notes

- **No Nucleo changes needed** - Protocol is already implemented in C++
- **Pick&Place protocol flexible** - Use SIMPLE for quick start, FULL later
- **Bootstrap mechanism** - Always syncs with MCU state on connect
- **MCU reset detection** - Automatically re-bootstraps if uptime drops
- **Thread-safe** - All serial I/O protected by locks

Enjoy building your HMI! 🚀
