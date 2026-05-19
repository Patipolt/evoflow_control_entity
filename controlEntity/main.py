"""
Entry point for the EvoFlow control entity application.

Creates the PySide6 application, instantiates the Logic coordinator,
and runs the event loop with clean shutdown handling.

Project: EvoFlow Innosuisse
Author: Patipol Thanuphol, Scientific Researcher at ZHAW — thau@zhaw.ch | patipol.thanu@gmail.com
Created: April 2026
"""

import sys
import os
from PySide6.QtWidgets import QApplication

# Add parent directory to Python path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from controlEntity.pages.main_ui import MainUI

def main():
    """Main entry point for the application."""
    app = QApplication(sys.argv)
    app.setApplicationName("Evoflow Control Entity")
    
    # Ensure application quits when last window is closed
    app.setQuitOnLastWindowClosed(True)
    
    # Create and show main window
    window = MainUI()
    window.show()
    
    try:
        # For now, just run the app
        # In real usage, you'd create the HMI here
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