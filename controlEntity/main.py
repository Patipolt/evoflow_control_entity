"""
Entry point for the EvoFlow GUI application.

Creates the PySide6 application, instantiates the Logic coordinator,
and runs the event loop with clean shutdown handling.

Project: EvoFlow Innosuisse
Author: Based on existing Enantios pattern
Created: April 2026
"""

import sys
import os
from PySide6.QtWidgets import QApplication

# Add parent directory to Python path if needed
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import will be created later - this is a placeholder
# from controlEntity.pages.main_ui import MainUI


def main():
    """Main entry point for the application."""
    app = QApplication(sys.argv)
    app.setApplicationName("EvoFlow Control")
    
    # Ensure application quits when last window is closed
    app.setQuitOnLastWindowClosed(True)
    
    # For now, just demonstrate the logic layer works
    from controlEntity.logic import Logic
    
    logic = Logic()
    
    print("=" * 60)
    print("EvoFlow GUI - Logic Layer Initialized")
    print("=" * 60)
    print("\nAvailable signals:")
    print("  EvoFlow:")
    print("    - evoflow_connect_requested.emit(port, node_id)")
    print("    - evoflow_set_temperature_requested.emit(heater_id, temp)")
    print("    - evoflow_set_velocity_requested.emit(pump_id, vel)")
    print("    - evoflow_start_requested.emit()")
    print("\n  Pick&Place:")
    print("    - pickplace_connect_requested.emit(port)")
    print("    - pickplace_move_requested.emit(x, y, z)")
    print("    - pickplace_gripper_requested.emit(True/False)")
    print("\nCreate your GUI and connect to these signals!")
    print("=" * 60)
    
    # TODO: Create and show main window
    # window = MainUI(logic)
    # window.show()
    
    try:
        # For now, just run the app
        # In real usage, you'd create the GUI here
        print("\nPress Ctrl+C to exit...")
        exit_code = app.exec()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
        os._exit(0)
    except Exception as e:
        print(f"Application error: {e}")
        import traceback
        traceback.print_exc()
        os._exit(1)


if __name__ == "__main__":
    main()
