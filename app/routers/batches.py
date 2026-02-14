from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..brewfather import fetch_batches, sync_batches_to_db
from ..database import get_db
from ..models import Batch

router = APIRouter(prefix="/api/batches", tags=["batches"])


@router.get("")
def list_batches(db: Session = Depends(get_db)):
    batches = db.query(Batch).order_by(Batch.brew_date.desc()).all()
    return [
        {
            "id": b.id,
            "batch_no": b.batch_no,
            "name": b.name,
            "style": b.style,
            "abv": b.abv,
            "brew_date": b.brew_date,
            "status": b.status,
            "recipe_name": b.recipe_name,
            "bottling_date": b.bottling_date,
            "batch_notes": b.batch_notes,
            "last_synced": b.last_synced.isoformat() if b.last_synced else None,
        }
        for b in batches
    ]


@router.post("/sync")
async def sync_from_brewfather(db: Session = Depends(get_db)):
    try:
        raw = await fetch_batches()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Brewfather API error: {e}")
    count = sync_batches_to_db(db, raw)
    return {"synced": count}
