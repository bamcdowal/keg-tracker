import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .database import Base, SessionLocal, engine
from .models import Keg, KegStatus
from .routers import batches, kegs, stats

Base.metadata.create_all(bind=engine)

# Seed the 16 kegs if they don't exist yet
db = SessionLocal()
if db.query(Keg).count() == 0:
    for i in range(1, 17):
        db.add(Keg(id=i, label=f"Keg #{i}", status=KegStatus.empty))
    db.commit()
db.close()

app = FastAPI(title="Keg Tracker")


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(kegs.router)
app.include_router(batches.router)
app.include_router(stats.router)

static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
