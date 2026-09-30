"""
Notification worker for handling notifications via ntfy.sh.

Project: EvoFlow Innosuisse
Author: Patipol Thanuphol, Scientific Researcher at ZHAW — thanuphol@zhaw.ch | patipol.thanuphol@gmail.com
Created: September 2026
"""

import requests

from PySide6.QtCore import QObject, QTimer, Signal, Slot

class NtfyWorker(QObject):
    """Worker class for sending notifications via ntfy.sh"""

    ntfy_hold_status_updated = Signal(bool)

    def __init__(self, topic: str):
        super().__init__()
        self.topic = topic
        self.base_url = f"https://ntfy.sh/{self.topic}"
        self.hold_status = False

    @Slot(str, str, int)
    def send_notification(self, title: str, message: str, priority: int = 3):
        """Send a notification with the given title and message."""
        if not self.hold_status:
            payload = {
                "title": title,
                "message": message,
                "priority": priority
            }
            try:
                response = requests.post(self.base_url, json=payload)
                if response.status_code == 200:
                    self.hold_status = True
                    self.ntfy_hold_status_updated.emit(self.hold_status)
                    print(f"Notification sent: {title} - {message}")
                else:
                    print(f"Failed to send notification: {response.status_code} - {response.text}")
            except Exception as e:
                print(f"Error sending notification: {e}")

    @Slot()
    def clear_hold_status(self):
        """Clear the hold status."""
        self.hold_status = False
        self.ntfy_hold_status_updated.emit(self.hold_status)