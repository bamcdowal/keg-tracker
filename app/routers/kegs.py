from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Batch, Keg, KegEvent, KegStatus

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


@router.post("")
def create_keg(db: Session = Depends(get_db)):
    max_id = db.query(func.max(Keg.id)).scalar() or 0
    keg = Keg(label=f"Keg #{max_id + 1}", status=KegStatus.empty)
    db.add(keg)
    db.commit()
    db.refresh(keg)
    return _keg_to_dict(keg)


@router.delete("/{keg_id}")
def delete_keg(keg_id: int, db: Session = Depends(get_db)):
    keg = db.get(Keg, keg_id)
    if not keg:
        raise HTTPException(status_code=404, detail="Keg not found")
    if keg.batch_id:
        raise HTTPException(status_code=400, detail="Cannot delete a keg with a batch assigned. Reset it first.")
    _log_event(db, keg_id, "deleted")
    db.delete(keg)
    db.commit()
    return {"ok": True}


PEOPLE = {"Michael", "Troy", "Brent"}


def _log_event(db: Session, keg_id: int, event_type: str, person: str = "",
               batch_id: str | None = None, batch_name: str = "", style: str = ""):
    db.add(KegEvent(
        keg_id=keg_id,
        event_type=event_type,
        person=person,
        batch_id=batch_id,
        batch_name=batch_name,
        style=style,
    ))


def _get_batch_info(db: Session, batch_id: str | None) -> tuple[str, str]:
    if not batch_id:
        return "", ""
    batch = db.get(Batch, batch_id)
    if not batch:
        return "", ""
    return batch.recipe_name or batch.name, batch.style


@router.put("/{keg_id}")
def update_keg(keg_id: int, data: KegUpdate, db: Session = Depends(get_db)):
    keg = db.get(Keg, keg_id)
    if not keg:
        raise HTTPException(status_code=404, detail="Keg not found")

    old_location = keg.location or ""
    old_batch_id = keg.batch_id
    old_status = keg.status

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

    # Log events for meaningful changes
    new_location = keg.location or ""
    batch_name, style = _get_batch_info(db, keg.batch_id)

    # Batch assigned
    if keg.batch_id and keg.batch_id != old_batch_id:
        _log_event(db, keg_id, "filled", batch_id=keg.batch_id,
                   batch_name=batch_name, style=style)

    # Assigned to a person
    if new_location in PEOPLE and new_location != old_location:
        _log_event(db, keg_id, "assigned", person=new_location,
                   batch_id=keg.batch_id, batch_name=batch_name, style=style)

    # Tapped
    if keg.status == KegStatus.on_tap and old_status != KegStatus.on_tap:
        _log_event(db, keg_id, "tapped", person=new_location,
                   batch_id=keg.batch_id, batch_name=batch_name, style=style)

    db.commit()
    db.refresh(keg)
    return _keg_to_dict(keg)


@router.post("/{keg_id}/reset")
def reset_keg(keg_id: int, db: Session = Depends(get_db)):
    keg = db.get(Keg, keg_id)
    if not keg:
        raise HTTPException(status_code=404, detail="Keg not found")

    # Log the return event before clearing data
    old_person = keg.location if keg.location in PEOPLE else ""
    if old_person or keg.batch_id:
        batch_name, style = _get_batch_info(db, keg.batch_id)
        _log_event(db, keg_id, "returned", person=old_person,
                   batch_id=keg.batch_id, batch_name=batch_name, style=style)

    keg.status = KegStatus.empty
    keg.batch_id = None
    keg.location = ""
    keg.date_purchased = ""
    keg.notes = ""

    db.commit()
    db.refresh(keg)
    return _keg_to_dict(keg)
