from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.camera import Camera
from app.schemas.camera import CameraCreate, CameraUpdate

router = APIRouter(prefix="/camera", tags=["Camera"])


# -----------------------------
# Get All Cameras
# -----------------------------
@router.get("/")
def get_cameras(db: Session = Depends(get_db)):
    return db.query(Camera).all()


# -----------------------------
# Get Single Camera
# -----------------------------
@router.get("/{camera_id}")
def get_camera(camera_id: int, db: Session = Depends(get_db)):
    camera = db.query(Camera).filter(Camera.id == camera_id).first()

    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")

    return camera


# -----------------------------
# Add Camera
# -----------------------------
@router.post("/")
def add_camera(camera: CameraCreate, db: Session = Depends(get_db)):
    new_camera = Camera(
        camera_name=camera.camera_name,
        location=camera.location,
        stream_url=camera.stream_url,
        status="Active",
    )

    db.add(new_camera)
    db.commit()
    db.refresh(new_camera)

    return new_camera


# -----------------------------
# Update Camera
# -----------------------------
@router.put("/{camera_id}")
def update_camera(
    camera_id: int,
    payload: CameraUpdate,
    db: Session = Depends(get_db),
):
    camera = db.query(Camera).filter(Camera.id == camera_id).first()

    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")

    data = payload.model_dump(exclude_none=True)

    for key, value in data.items():
        setattr(camera, key, value)

    db.commit()
    db.refresh(camera)

    return camera


# -----------------------------
# Delete Camera
# -----------------------------
@router.delete("/{camera_id}")
def delete_camera(
    camera_id: int,
    db: Session = Depends(get_db),
):
    camera = db.query(Camera).filter(Camera.id == camera_id).first()

    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")

    # Prevent deleting the default webcam
    if camera.stream_url == "0":
        raise HTTPException(
            status_code=400,
            detail="Primary Webcam cannot be deleted.",
        )

    db.delete(camera)
    db.commit()

    return {
        "message": "Camera deleted successfully"
    }