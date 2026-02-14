import os
from datetime import datetime

import httpx
from dotenv import load_dotenv
from sqlalchemy.orm import Session

from .models import Batch

load_dotenv()

BREWFATHER_BASE_URL = "https://api.brewfather.app/v2"


def _get_auth() -> tuple[str, str]:
    user_id = os.getenv("BREWFATHER_USER_ID", "")
    api_key = os.getenv("BREWFATHER_API_KEY", "")
    return (user_id, api_key)


async def fetch_batches() -> list[dict]:
    """Fetch all batches from Brewfather API."""
    auth = _get_auth()
    print(f"[SYNC] Starting Brewfather sync (user_id={auth[0][:4]}…)" if auth[0] else "[SYNC] WARNING: BREWFATHER_USER_ID is empty!")
    if not auth[1]:
        print("[SYNC] WARNING: BREWFATHER_API_KEY is empty!")
    batches = []
    seen_ids = set()
    offset = 0
    limit = 50

    async with httpx.AsyncClient(timeout=30.0) as client:
        for _ in range(20):  # safety cap: max 1000 batches
            print(f"[SYNC] Requesting batches offset={offset} limit={limit}")
            resp = await client.get(
                f"{BREWFATHER_BASE_URL}/batches",
                auth=auth,
                params={
                    "limit": limit,
                    "offset": offset,
                    "status": "Conditioning",
                    "include": "recipe.name,recipe.style.name,measuredAbv,batchNo,bottlingDate,note",
                },
            )
            print(f"[SYNC] Brewfather responded: {resp.status_code}")
            resp.raise_for_status()
            page = resp.json()
            if not page:
                break

            # Stop if we start getting duplicates
            new_count = 0
            for b in page:
                bid = b.get("_id", "")
                if bid not in seen_ids:
                    seen_ids.add(bid)
                    batches.append(b)
                    new_count += 1

            print(f"[SYNC] Got {len(page)} items, {new_count} new")
            if new_count == 0 or len(page) < limit:
                break
            offset += limit

    print(f"[SYNC] Fetched {len(batches)} unique batches total")
    return batches



def sync_batches_to_db(db: Session, raw_batches: list[dict]) -> int:
    """Upsert Brewfather batches into the local database. Returns count synced."""
    count = 0
    for b in raw_batches:
        batch_id = b.get("_id", "")
        existing = db.get(Batch, batch_id)

        def _parse_date(ms):
            if not ms:
                return ""
            try:
                return datetime.fromtimestamp(ms / 1000).strftime("%Y-%m-%d")
            except (ValueError, TypeError, OSError):
                return str(ms)

        values = {
            "batch_no": b.get("batchNo"),
            "name": b.get("name", ""),
            "style": b.get("recipe", {}).get("style", {}).get("name", "")
            if isinstance(b.get("recipe"), dict)
            else "",
            "abv": b.get("measuredAbv"),
            "brew_date": _parse_date(b.get("brewDate")),
            "bottling_date": _parse_date(b.get("bottlingDate")),
            "status": b.get("status", ""),
            "recipe_name": b.get("recipe", {}).get("name", "")
            if isinstance(b.get("recipe"), dict)
            else "",
            "batch_notes": b.get("note", "") or "",
            "last_synced": datetime.utcnow(),
        }

        if existing:
            for k, v in values.items():
                setattr(existing, k, v)
        else:
            db.add(Batch(id=batch_id, **values))
        count += 1

    db.commit()
    return count
