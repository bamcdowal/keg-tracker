from collections import defaultdict
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import KegEvent

router = APIRouter(prefix="/api/stats", tags=["stats"])

KEG_LITRES = 19


@router.get("")
def get_stats(db: Session = Depends(get_db)):
    events = db.query(KegEvent).order_by(KegEvent.timestamp).all()

    # Build assignment timeline: track assigned→returned pairs per person
    # An "assigned" event starts a keg for a person
    # A "returned" event ends it
    active_kegs: dict[int, dict] = {}  # keg_id → assignment info
    completed: list[dict] = []

    for ev in events:
        if ev.event_type == "assigned" and ev.person:
            active_kegs[ev.keg_id] = {
                "person": ev.person,
                "batch_id": ev.batch_id,
                "batch_name": ev.batch_name,
                "style": ev.style,
                "assigned_at": ev.timestamp,
            }
        elif ev.event_type == "returned":
            assignment = active_kegs.pop(ev.keg_id, None)
            if assignment:
                days = (ev.timestamp - assignment["assigned_at"]).total_seconds() / 86400
                completed.append({
                    "person": assignment["person"],
                    "batch_name": assignment["batch_name"],
                    "style": assignment["style"],
                    "days": round(days, 1),
                    "assigned_at": assignment["assigned_at"].isoformat(),
                    "returned_at": ev.timestamp.isoformat(),
                })
            elif ev.person:
                # No matching assignment, still record as a return
                completed.append({
                    "person": ev.person,
                    "batch_name": ev.batch_name,
                    "style": ev.style,
                    "days": 0,
                    "assigned_at": ev.timestamp.isoformat(),
                    "returned_at": ev.timestamp.isoformat(),
                })

    # Per-person stats
    person_stats: dict[str, dict] = {}
    for c in completed:
        p = c["person"]
        if not p:
            continue
        if p not in person_stats:
            person_stats[p] = {
                "kegs": 0,
                "litres": 0,
                "total_days": 0,
                "styles": defaultdict(int),
                "batches": defaultdict(int),
                "history": [],
            }
        ps = person_stats[p]
        ps["kegs"] += 1
        ps["litres"] += KEG_LITRES
        ps["total_days"] += c["days"]
        if c["style"]:
            ps["styles"][c["style"]] += 1
        if c["batch_name"]:
            ps["batches"][c["batch_name"]] += 1
        ps["history"].append(c)

    # Format person stats for response
    people = []
    for name, ps in sorted(person_stats.items()):
        avg_days = round(ps["total_days"] / ps["kegs"], 1) if ps["kegs"] > 0 else 0
        top_styles = sorted(ps["styles"].items(), key=lambda x: -x[1])[:3]
        top_batches = sorted(ps["batches"].items(), key=lambda x: -x[1])[:3]

        # Consumption rate: litres per month
        if ps["history"]:
            first = datetime.fromisoformat(ps["history"][0]["assigned_at"])
            last = datetime.fromisoformat(ps["history"][-1]["returned_at"])
            span_days = max((last - first).total_seconds() / 86400, 1)
            litres_per_month = round(ps["litres"] / (span_days / 30), 1)
        else:
            litres_per_month = 0

        people.append({
            "name": name,
            "kegs_consumed": ps["kegs"],
            "litres_consumed": ps["litres"],
            "avg_days_per_keg": avg_days,
            "litres_per_month": litres_per_month,
            "top_styles": [{"name": s, "count": c} for s, c in top_styles],
            "top_batches": [{"name": b, "count": c} for b, c in top_batches],
            "history": ps["history"][-10:],  # last 10
        })

    # Overall stats
    total_kegs = sum(p["kegs_consumed"] for p in people)
    total_litres = total_kegs * KEG_LITRES

    # All events counts
    filled_count = sum(1 for e in events if e.event_type == "filled")
    returned_count = sum(1 for e in events if e.event_type == "returned")

    # Monthly breakdown
    monthly: dict[str, int] = defaultdict(int)
    for c in completed:
        month_key = c["returned_at"][:7]  # YYYY-MM
        monthly[month_key] += 1
    monthly_sorted = [{"month": k, "kegs": v} for k, v in sorted(monthly.items())]

    # Style popularity across all people
    all_styles: dict[str, int] = defaultdict(int)
    for c in completed:
        if c["style"]:
            all_styles[c["style"]] += 1
    popular_styles = [{"name": s, "count": c} for s, c in
                      sorted(all_styles.items(), key=lambda x: -x[1])[:5]]

    return {
        "people": people,
        "overall": {
            "total_kegs_consumed": total_kegs,
            "total_litres": total_litres,
            "total_filled": filled_count,
            "total_returned": returned_count,
            "monthly": monthly_sorted,
            "popular_styles": popular_styles,
        },
        "event_count": len(events),
    }


@router.get("/events")
def get_events(db: Session = Depends(get_db)):
    events = db.query(KegEvent).order_by(KegEvent.timestamp.desc()).limit(50).all()
    return [
        {
            "id": e.id,
            "keg_id": e.keg_id,
            "event_type": e.event_type,
            "person": e.person,
            "batch_name": e.batch_name,
            "style": e.style,
            "timestamp": e.timestamp.isoformat(),
        }
        for e in events
    ]
