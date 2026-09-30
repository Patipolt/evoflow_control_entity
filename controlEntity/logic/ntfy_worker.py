"""
Notification worker for handling notifications via ntfy.sh.

Project: EvoFlow Innosuisse
Author: Patipol Thanuphol, Scientific Researcher at ZHAW — thanuphol@zhaw.ch | patipol.thanuphol@gmail.com
Created: September 2026
"""

import requests
import json
import logging

class NtfyWorker:
    """Worker class for sending notifications via ntfy.sh"""

    def __init__(self, topic: str):
        self.topic = topic
        self.base_url = f"https://ntfy.sh/{self.topic}"
        self.hold_status = False
        logging.info(f"NtfyWorker initialized for topic: {self.topic}")

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
                    logging.info(f"Notification sent successfully: {title} - {message}")
                else:
                    logging.error(f"Failed to send notification: {response.status_code} - {response.text}")
            except Exception as e:
                logging.error(f"Exception occurred while sending notification: {e}")

    def clear_hold_status(self):
        """Clear the hold status."""
        self.hold_status = False
        logging.info("Hold status cleared.")