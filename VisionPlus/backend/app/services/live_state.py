"""
In-process state machine for the live monitoring stream.
"""

from __future__ import annotations

import threading
import time


class LiveMonitorState:
    def __init__(self):
        self._lock = threading.Lock()

        self.is_running = False
        self.is_paused = False
        self.detection_enabled = True

        # Default laptop webcam
        self.camera_index = 0

        # Selected database camera (None = use laptop webcam)
        self.camera_id = None

        self.started_at = None

        self.stats = {
            "people_count": 0,
            "vehicle_count": 0,
            "object_count": 0,
            "risk_level": "LOW",
            "fps": 0.0,
            "latency_ms": 0.0,
            "frame_time": None,
            "camera_status": "unknown",
            "connection_status": "disconnected",
            "zones": {
                "Zone A": 0,
                "Zone B": 0,
                "Zone C": 0,
                "Zone D": 0,
            },
            "recommendation": "Crowd density is normal.",
        }

    def start(self) -> None:
        with self._lock:
            self.is_running = True
            self.is_paused = False
            self.started_at = time.time()
            self.stats["connection_status"] = "connecting"

    def stop(self) -> None:
        with self._lock:
            self.is_running = False
            self.is_paused = False
            self.started_at = None

            self.stats.update({
                "connection_status": "disconnected",
                "camera_status": "unknown",
                "people_count": 0,
                "vehicle_count": 0,
                "object_count": 0,
                "fps": 0.0,
                "latency_ms": 0.0,
                "risk_level": "LOW",
                "zones": {
                    "Zone A": 0,
                    "Zone B": 0,
                    "Zone C": 0,
                    "Zone D": 0,
                },
                "recommendation": "Monitoring stopped.",
            })

    def pause(self) -> None:
        with self._lock:
            if self.is_running:
                self.is_paused = True

    def resume(self) -> None:
        with self._lock:
            if self.is_running:
                self.is_paused = False

    def restart(self) -> None:
        with self._lock:
            self.is_running = False
            self.is_paused = False
            self.started_at = time.time()
            self.is_running = True
            self.stats["connection_status"] = "connecting"

    def toggle_detection(self) -> bool:
        with self._lock:
            self.detection_enabled = not self.detection_enabled
            return self.detection_enabled

    def update_stats(self, **kwargs) -> None:
        with self._lock:
            self.stats.update(kwargs)

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "is_running": self.is_running,
                "is_paused": self.is_paused,
                "detection_enabled": self.detection_enabled,
                "camera_id": self.camera_id,
                "camera_index": self.camera_index,
                "started_at": self.started_at,
                **self.stats,
            }


# Global singleton
live_state = LiveMonitorState()