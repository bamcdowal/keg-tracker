import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from sqlalchemy import text

from .database import Base, SessionLocal, engine
from .models import BrewerySettings, Keg, KegStatus, Location, Person
from .routers import batches, kegs, people, settings, stats

Base.metadata.create_all(bind=engine)

# Safe migration: add keg_volume_litres column if it doesn't exist yet
with engine.connect() as _conn:
    try:
        _conn.execute(text("ALTER TABLE brewery_settings ADD COLUMN keg_volume_litres REAL DEFAULT 19.0"))
        _conn.commit()
    except Exception:
        pass  # Column already exists

# Seed initial data
with SessionLocal() as db:
    if db.query(Keg).count() == 0:
        for i in range(1, 17):
            db.add(Keg(id=i, label=f"Keg #{i}", status=KegStatus.empty))
        db.commit()
    if db.query(Person).count() == 0:
        for name in ["Michael", "Troy", "Brent"]:
            db.add(Person(name=name))
        db.commit()
    if db.query(Location).count() == 0:
        db.add(Location(name="Conditioning Fridge"))
        db.commit()
    if db.query(BrewerySettings).count() == 0:
        db.add(BrewerySettings(id=1, name="Blue Dog Brewing"))
        db.commit()

app = FastAPI(title="Keg Tracker")


class NoCacheStaticMiddleware(BaseHTTPMiddleware):
    """Prevent browsers from serving stale static files."""

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        path = request.url.path
        if path.endswith((".js", ".css", ".html")) or path == "/":
            response.headers["Cache-Control"] = "no-cache, must-revalidate"
        return response


app.add_middleware(NoCacheStaticMiddleware)

_VERSION_FILE = Path(__file__).parent.parent / "VERSION"


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/version")
def get_version():
    try:
        version = _VERSION_FILE.read_text().strip()
    except Exception:
        version = "unknown"
    return {"version": version}


app.include_router(kegs.router)
app.include_router(batches.router)
app.include_router(stats.router)
app.include_router(people.router)
app.include_router(people.locations_router)
app.include_router(settings.router)

static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
