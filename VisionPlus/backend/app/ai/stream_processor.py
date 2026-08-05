"""
Extended for Live Monitoring controls: process_frame() now returns a full
stats dict (people/vehicle/object counts, risk, per-frame latency) instead
of just a people count, and accepts detection_enabled=False so the
Detection Toggle in the UI can show a raw feed without running YOLO.
"""
import time

import cv2

from app.ai.yolo_detector import detect
from app.ai.tracker import make_tracker, track
from app.ai.draw import draw
from app.ai.risk_score import calculate_risk
from app.ai.detection_classes import DETECT_CLASSES, classify_counts

# Each live monitoring session gets its own tracker instance, reset via
# reset_live_tracker() whenever Start/Restart is pressed (see live_state.py)
# so tracker IDs don't leak across sessions — the same bug class that was
# already fixed for offline analysis (see app/ai/tracker.py docstring).
_live_tracker = None


def get_live_tracker():
    global _live_tracker
    if _live_tracker is None:
        _live_tracker = make_tracker()
    return _live_tracker


def reset_live_tracker():
    global _live_tracker
    _live_tracker = None


def process_frame(frame, detection_enabled: bool = True):
    """Detect, track, annotate a single live frame."""

    start = time.perf_counter()

    if not detection_enabled:
        latency_ms = round((time.perf_counter() - start) * 1000, 1)
        return frame, {
            "people_count": 0,
            "vehicle_count": 0,
            "object_count": 0,
            "risk_level": "LOW",
            "latency_ms": latency_ms,
            "zones": {
                "Zone A": 0,
                "Zone B": 0,
                "Zone C": 0,
                "Zone D": 0,
            },
            "recommendation": "Detection Disabled",
        }

    results = detect(frame, classes=DETECT_CLASSES)
    result = results[0]

    tracked = track(result, get_live_tracker())

    counts = classify_counts(tracked)
    risk = calculate_risk(counts["people"])

    # -------------------------------
    # Live Zone Analytics
    # -------------------------------
    height, width = frame.shape[:2]

    zone_a = zone_b = zone_c = zone_d = 0

    if tracked.class_id is not None:
        for box, class_id in zip(tracked.xyxy, tracked.class_id):

            # Count only persons
            if int(class_id) != 0:
                continue

            x1, y1, x2, y2 = box

            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2

            if center_x < width / 2 and center_y < height / 2:
                zone_a += 1

            elif center_x >= width / 2 and center_y < height / 2:
                zone_b += 1

            elif center_x < width / 2 and center_y >= height / 2:
                zone_c += 1

            else:
                zone_d += 1

    zones = {
        "Zone A": zone_a,
        "Zone B": zone_b,
        "Zone C": zone_c,
        "Zone D": zone_d,
    }

    # -------------------------------
    # AI Recommendation
    # -------------------------------
    highest_zone = max(zones, key=zones.get)
    highest_count = zones[highest_zone]

    if highest_count == 0:
        recommendation = "Crowd density is normal."

    elif highest_count < 5:
        recommendation = f"Monitor {highest_zone}."

    elif highest_count < 10:
        recommendation = f"Moderate crowd in {highest_zone}."

    else:
        recommendation = (
            f"High crowd density detected in {highest_zone}. "
            "Deploy security personnel."
        )

    # -------------------------------
    # Draw detections
    # -------------------------------
    annotated = draw(frame, tracked)

    # -------------------------------
    # Draw Zone Boundaries
    # -------------------------------
    h, w = annotated.shape[:2]

    # Vertical
    cv2.line(annotated, (w // 2, 0), (w // 2, h), (255, 0, 255), 2)

    # Horizontal
    cv2.line(annotated, (0, h // 2), (w, h // 2), (255, 0, 255), 2)

  
    latency_ms = round((time.perf_counter() - start) * 1000, 1)

    return annotated, {
        "people_count": counts["people"],
        "vehicle_count": counts["vehicles"],
        "object_count": counts["objects"],
        "risk_level": risk,
        "latency_ms": latency_ms,
        "zones": zones,
        "recommendation": recommendation,
    }


