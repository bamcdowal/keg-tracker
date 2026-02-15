from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Location, Person

router = APIRouter(prefix="/api/people", tags=["people"])


class PersonCreate(BaseModel):
    name: str


class LocationCreate(BaseModel):
    name: str


@router.get("")
def list_people(db: Session = Depends(get_db)):
    people = db.query(Person).order_by(Person.name).all()
    return [{"id": p.id, "name": p.name} for p in people]


@router.post("")
def create_person(data: PersonCreate, db: Session = Depends(get_db)):
    name = data.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name cannot be empty")
    existing = db.query(Person).filter(Person.name == name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Person already exists")
    if db.query(Location).filter(Location.name == name).first():
        raise HTTPException(status_code=400, detail="A location with this name already exists")
    person = Person(name=name)
    db.add(person)
    db.commit()
    db.refresh(person)
    return {"id": person.id, "name": person.name}


@router.delete("/{person_id}")
def delete_person(person_id: int, db: Session = Depends(get_db)):
    person = db.get(Person, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    db.delete(person)
    db.commit()
    return {"ok": True}


locations_router = APIRouter(prefix="/api/locations", tags=["locations"])


@locations_router.get("")
def list_locations(db: Session = Depends(get_db)):
    locations = db.query(Location).order_by(Location.name).all()
    return [{"id": loc.id, "name": loc.name} for loc in locations]


@locations_router.post("")
def create_location(data: LocationCreate, db: Session = Depends(get_db)):
    name = data.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name cannot be empty")
    existing = db.query(Location).filter(Location.name == name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Location already exists")
    if db.query(Person).filter(Person.name == name).first():
        raise HTTPException(status_code=400, detail="A person with this name already exists")
    location = Location(name=name)
    db.add(location)
    db.commit()
    db.refresh(location)
    return {"id": location.id, "name": location.name}


@locations_router.delete("/{location_id}")
def delete_location(location_id: int, db: Session = Depends(get_db)):
    location = db.get(Location, location_id)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    db.delete(location)
    db.commit()
    return {"ok": True}
