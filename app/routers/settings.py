import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import DATABASE_URL, get_db
from ..models import BrewerySettings

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _get_data_dir() -> Path:
    """Derive data directory from DATABASE_URL (parent of the .db file)."""
    url = DATABASE_URL
    if url.startswith("sqlite:///"):
        db_path = Path(url.replace("sqlite:///", "", 1))
        return db_path.parent.resolve()
    return Path(".").resolve()


def _get_settings(db: Session) -> BrewerySettings:
    settings = db.get(BrewerySettings, 1)
    if not settings:
        settings = BrewerySettings(id=1)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


class BreweryNameUpdate(BaseModel):
    name: str


@router.get("/brewery")
def get_brewery(db: Session = Depends(get_db)):
    settings = _get_settings(db)
    logo_url = "/api/settings/logo" if settings.has_custom_logo else "/logo.png"
    return {"name": settings.name, "logo_url": logo_url}


@router.put("/brewery")
def update_brewery(data: BreweryNameUpdate, db: Session = Depends(get_db)):
    name = data.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name cannot be empty")
    settings = _get_settings(db)
    settings.name = name
    db.commit()
    logo_url = "/api/settings/logo" if settings.has_custom_logo else "/logo.png"
    return {"name": settings.name, "logo_url": logo_url}


@router.post("/logo")
async def upload_logo(file: UploadFile, db: Session = Depends(get_db)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    ext = Path(file.filename).suffix.lower() if file.filename else ".png"
    if ext not in (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"):
        ext = ".png"

    data_dir = _get_data_dir()

    # Remove any existing custom logo files
    for existing in data_dir.glob("custom_logo.*"):
        existing.unlink()

    logo_path = data_dir / f"custom_logo{ext}"
    contents = await file.read()
    logo_path.write_bytes(contents)

    settings = _get_settings(db)
    settings.has_custom_logo = True
    db.commit()

    return {"logo_url": "/api/settings/logo"}


@router.delete("/logo")
def delete_logo(db: Session = Depends(get_db)):
    data_dir = _get_data_dir()
    for existing in data_dir.glob("custom_logo.*"):
        existing.unlink()

    settings = _get_settings(db)
    settings.has_custom_logo = False
    db.commit()

    return {"logo_url": "/logo.png"}


@router.get("/logo")
def get_logo():
    data_dir = _get_data_dir()
    for logo_file in data_dir.glob("custom_logo.*"):
        ext = logo_file.suffix.lower()
        media_types = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".svg": "image/svg+xml",
            ".webp": "image/webp",
        }
        return FileResponse(
            str(logo_file),
            media_type=media_types.get(ext, "image/png"),
        )
    raise HTTPException(status_code=404, detail="No custom logo found")
