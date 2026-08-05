"""
Live Monitoring API.

BEFORE: a single GET /stream/ endpoint that unconditionally opened the
server's webcam and streamed MJPEG forever — no start/stop, no stats, no
way to know if a camera was even present without opening the <img> tag.

NOW: a real control plane (start/stop/pause/resume/restart/detection
toggle) backed by app/services/live_state.py, plus GET /stream/status for
polling current people/vehicle/object counts, FPS, latency, and
camera/connection status from outside the MJPEG stream (e.g. the dashboard
widgets, which can't parse a multipart stream).
"""
import time

import cv2
import numpy as np
from fastapi import APIRouter, Body
from fastapi.responses import StreamingResponse

from app.ai.stream_processor import process_frame, reset_live_tracker
from app.services.live_state import live_state
from app.db.database import SessionLocal
from app.models.camera import Camera

router = APIRouter(prefix="/stream", tags=["Live Stream"])


def _placeholder_jpeg(message: str, color=(0, 0, 255)) -> bytes:
    blank = np.zeros((480, 640, 3), dtype="uint8")
    cv2.putText(blank, message, (30, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
    _, buf = cv2.imencode(".jpg", blank)
    return buf.tobytes()


def _mjpeg_chunk(jpg_bytes: bytes) -> bytes:
    return b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpg_bytes + b"\r\n"


def _generate_frames():
    # Not started
    if not live_state.is_running:
        yield _mjpeg_chunk(
            _placeholder_jpeg(
                "Monitoring stopped - press Start",
                (0, 165, 255),
            )
        )
        return

    # ---------------------------------
    # Open selected camera
    # ---------------------------------
    db = SessionLocal()

    # Default = Laptop Webcam
    source = 0

    # If user selected a camera from database
    if getattr(live_state, "camera_id", None) is not None:
        camera = (
            db.query(Camera)
            .filter(Camera.id == live_state.camera_id)
            .first()
        )

        if camera:
            source = camera.stream_url

    db.close()

    # Webcam indexes ("0","1") → int
    try:
        source = int(source)
    except (ValueError, TypeError):
        pass

    cap = cv2.VideoCapture(source)

    # Camera failed
# Camera failed
    if not cap.isOpened():
        live_state.update_stats(
            camera_status="unavailable",
            connection_status="error",
            people_count=0,
            vehicle_count=0,
            object_count=0,
            fps=0.0,
            latency_ms=0.0,
            risk_level="LOW",
            zones={
                "Zone A": 0,
                "Zone B": 0,
                "Zone C": 0,
                "Zone D": 0,
            },
            recommendation="Camera unavailable.",
        )

        yield _mjpeg_chunk(
            _placeholder_jpeg(
                "No camera available",
                (0, 0, 255),
            )
        )
        return

    live_state.update_stats(
        camera_status="connected",
        connection_status="connected",
    )

    frame_count = 0
    window_start = time.time()
    last_annotated = None

    try:
        while live_state.is_running:

            if live_state.is_paused:
                if last_annotated is not None:
                    _, buf = cv2.imencode(".jpg", last_annotated)
                    yield _mjpeg_chunk(buf.tobytes())
                else:
                    yield _mjpeg_chunk(
                        _placeholder_jpeg(
                            "Paused",
                            (255, 165, 0),
                        )
                    )

                time.sleep(0.2)
                continue

            ok, frame = cap.read()

            if not ok:
                live_state.update_stats(
                    camera_status="error",
                    connection_status="error",
                )

                yield _mjpeg_chunk(
                    _placeholder_jpeg(
                        "Camera read failed",
                        (0, 0, 255),
                    )
                )
                break

            annotated, stats = process_frame(
                frame,
                detection_enabled=live_state.detection_enabled,
            )

            last_annotated = annotated

            frame_count += 1
            elapsed = time.time() - window_start

            fps = (
                round(frame_count / elapsed, 1)
                if elapsed > 0
                else 0.0
            )

            live_state.update_stats(
                frame_time=time.time(),
                fps=fps,
                camera_status="connected",
                connection_status="connected",

                people_count=stats["people_count"],
                vehicle_count=stats["vehicle_count"],
                object_count=stats["object_count"],
                risk_level=stats["risk_level"],
                latency_ms=stats["latency_ms"],

                zones=stats.get(
                    "zones",
                    {
                        "Zone A": 0,
                        "Zone B": 0,
                        "Zone C": 0,
                        "Zone D": 0,
                    },
                ),

                recommendation=stats.get(
                    "recommendation",
                    "Crowd density is normal.",
                ),
            )

            _, buffer = cv2.imencode(".jpg", annotated)
            yield _mjpeg_chunk(buffer.tobytes())

    finally:
        cap.release()

        live_state.update_stats(
            camera_status="unknown",
            connection_status="disconnected",
            people_count=0,
            vehicle_count=0,
            object_count=0,
            fps=0.0,
            latency_ms=0.0,
            risk_level="LOW",
            zones={
                "Zone A": 0,
                "Zone B": 0,
                "Zone C": 0,
                "Zone D": 0,
            },
            recommendation="No active camera.",
        )


@router.get("/")
def stream():
    """MJPEG stream. Safe to leave mounted in an <img> tag at all times —
    it renders a placeholder until /stream/start is called."""
    return StreamingResponse(
        _generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )

@router.get("/status")
def status():
    """Poll current live-monitoring state + latest per-frame stats.
    Used by the dashboard and Live Monitoring page — does not require
    parsing the MJPEG stream itself."""
    return live_state.snapshot()




@router.post("/start")
def start(payload: dict = Body(default={})):
    reset_live_tracker()

    live_state.camera_id = payload.get("camera_id")

    live_state.start()

    return live_state.snapshot()

@router.post("/stop")
def stop():
    live_state.stop()
    return live_state.snapshot()


@router.post("/pause")
def pause():
    live_state.pause()
    return live_state.snapshot()


@router.post("/resume")
def resume():
    live_state.resume()
    return live_state.snapshot()


@router.post("/restart")
def restart():
    reset_live_tracker()
    live_state.restart()
    return live_state.snapshot()


@router.post("/detection-toggle")
def detection_toggle():
    enabled = live_state.toggle_detection()
    return {"detection_enabled": enabled}
