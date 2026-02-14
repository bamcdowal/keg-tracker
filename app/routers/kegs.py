from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Keg, KegStatus

router = APIRouter(prefix="/api/kegs", tags=["kegs"])


class KegUpdate(BaseModel):
    label: str | None = None
    status: KegStatus | None = None
    location: str | None = None
    batch_id: str | None = None
    date_purchased: str | None = None
    notes: str | None = None
    clear_batch: bool = False


def _keg_to_dict(keg: Keg) -> dict:
    return {
        "id": keg.id,
        "label": keg.label,
        "status": keg.status.value,
        "location": keg.location,
        "batch_id": keg.batch_id,
        "date_purchased": keg.date_purchased,
        "notes": keg.notes,
        "batch": {
            "id": keg.batch.id,
            "batch_no": keg.batch.batch_no,
            "name": keg.batch.name,
            "style": keg.batch.style,
            "abv": keg.batch.abv,
            "recipe_name": keg.batch.recipe_name,
            "bottling_date": keg.batch.bottling_date,
            "batch_notes": keg.batch.batch_notes,
        }
        if keg.batch
        else None,
    }


@router.get("")
def list_kegs(db: Session = Depends(get_db)):
    kegs = db.query(Keg).order_by(Keg.id).all()
    return [_keg_to_dict(k) for k in kegs]


@router.put("/{keg_id}")
def update_keg(keg_id: int, data: KegUpdate, db: Session = Depends(get_db)):
    keg = db.get(Keg, keg_id)
    if not keg:
        raise HTTPException(status_code=404, detail="Keg not found")

    if data.label is not None:
        keg.label = data.label
    if data.status is not None:
        keg.status = data.status
    if data.location is not None:
        keg.location = data.location
    if data.clear_batch:
        keg.batch_id = None
    elif data.batch_id is not None:
        keg.batch_id = data.batch_id
    if data.date_purchased is not None:
        keg.date_purchased = data.date_purchased
    if data.notes is not None:
        keg.notes = data.notes

    db.commit()
    db.refresh(keg)
    return _keg_to_dict(keg)


@router.post("/{keg_id}/reset")
def reset_keg(keg_id: int, db: Session = Depends(get_db)):
    keg = db.get(Keg, keg_id)
    if not keg:
        raise HTTPException(status_code=404, detail="Keg not found")

    keg.status = KegStatus.empty
    keg.batch_id = None
    keg.location = ""
    keg.date_purchased = ""
    keg.notes = ""

    db.commit()
    db.refresh(keg)
    return _keg_to_dict(keg)
