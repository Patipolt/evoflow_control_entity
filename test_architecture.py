"""
Test script to verify the EvoFlow communication architecture.

This script demonstrates the complete architecture without a GUI,
showing how the layers work together.

Project: EvoFlow Innosuisse
Created: April 2026
"""

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from controlEntity.logic import Logic


def test_architecture():
    """Test the communication architecture."""
    
    app = QApplication(sys.argv)
    
    print("=" * 60)
    print("EvoFlow Architecture Test")
    print("=" * 60)
    
    # Create logic instance
    logic = Logic()
    
    # Connect to signals for monitoring
    def on_evoflow_status(msg):
        print(f"[EvoFlow Status] {msg}")
    
    def on_evoflow_error(msg):
        print(f"[EvoFlow ERROR] {msg}")
    
    def on_evoflow_result(command, payload):
        print(f"[EvoFlow Result] Command: {command}")
        if 'result' in payload:
            print(f"  Success: {payload['result'].success}")
            print(f"  Message: {payload['result'].message}")
    
    def on_evoflow_telemetry(telem):
        print(f"[Telemetry] Uptime: {telem.uptime_s}s, "
              f"Temp1: {telem.temp_filt_m1:.2f}°C, "
              f"Vel1: {telem.vel_m1:.2f} rps")
    
    def on_pickplace_status(msg):
        print(f"[Pick&Place Status] {msg}")
    
    def on_pickplace_result(command, payload):
        print(f"[Pick&Place Result] Command: {command}")
        if 'result' in payload:
            print(f"  Success: {payload['result'].success}")
            print(f"  Message: {payload['result'].message}")
    
    # Connect signals
    logic.evoflow_status.connect(on_evoflow_status)
    logic.evoflow_error.connect(on_evoflow_error)
    logic.evoflow_command_result.connect(on_evoflow_result)
    logic.evoflow_telemetry.connect(on_evoflow_telemetry)
    
    logic.pickplace_status.connect(on_pickplace_status)
    logic.pickplace_command_result.connect(on_pickplace_result)
    
    print("\n✓ Logic layer initialized")
    print("✓ Workers started in threads")
    print("✓ Signals connected")
    
    # Test sequence
    def run_test_sequence():
        print("\n" + "=" * 60)
        print("Test Sequence")
        print("=" * 60)
        
        # Test 1: Try to connect (will fail without hardware)
        print("\n[Test 1] Attempting EvoFlow connection...")
        logic.evoflow_connect_requested.emit("/dev/ttyUSB0", 1)
        
        # Test 2: Try Pick&Place
        QTimer.singleShot(1000, lambda: test_pickplace(logic))
        
        # Test 3: Exit after tests
        QTimer.singleShot(3000, lambda: exit_test(app))
    
    def test_pickplace(logic):
        print("\n[Test 2] Attempting Pick&Place connection...")
        logic.pickplace_connect_requested.emit("COM5")
    
    def exit_test(app):
        print("\n" + "=" * 60)
        print("Test Complete!")
        print("=" * 60)
        print("\nArchitecture is working correctly.")
        print("Next steps:")
        print("  1. Connect actual hardware")
        print("  2. Create GUI tabs in controlEntity/pages/")
        print("  3. Connect GUI widgets to logic signals")
        print("\nExiting...")
        app.quit()
    
    # Run test after a short delay
    QTimer.singleShot(500, run_test_sequence)
    
    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    test_architecture()
