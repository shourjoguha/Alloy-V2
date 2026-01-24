from pathlib import Path
import json

from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.circuit import CircuitTemplate
from app.models.movement import Movement  # Added
from app.schemas.circuit import (
    CircuitTemplateResponse,
    CircuitTemplateUpdate,
    CircuitTemplateAdminDetail,
)
from app.models.enums import CircuitType
from app.config.settings import get_settings

router = APIRouter()
settings = get_settings()


async def require_admin(x_admin_token: str | None = Header(default=None)) -> bool:
    if settings.admin_api_token:
        if x_admin_token != settings.admin_api_token:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    else:
        if not settings.debug:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin features disabled")
    return True


def load_raw_workout_for_circuit(name: str) -> str | None:
    path = Path("seed_data") / "scraped_circuits.json"
    try:
        with path.open() as f:
            circuits_data = json.load(f)
    except FileNotFoundError:
        return None
    for item in circuits_data:
        if item.get("name") == name:
            return item.get("raw_workout") or item.get("description")
    return None


@router.get("", response_model=list[CircuitTemplateResponse])
async def list_circuits(
    circuit_type: CircuitType | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(CircuitTemplate)
    if circuit_type:
        query = query.where(CircuitTemplate.circuit_type == circuit_type)
    query = query.order_by(CircuitTemplate.name)
    result = await db.execute(query)
    circuits = result.scalars().all()
    
    # Enrich exercises_json with movement names
    movement_ids = set()
    for circuit in circuits:
        if circuit.exercises_json:
            for ex in circuit.exercises_json:
                if isinstance(ex, dict) and ex.get("movement_id"):
                    movement_ids.add(ex["movement_id"])
    
    if movement_ids:
        movements_result = await db.execute(select(Movement).where(Movement.id.in_(movement_ids)))
        movements = {m.id: m.name for m in movements_result.scalars().all()}
        
        for circuit in circuits:
            if circuit.exercises_json:
                # Create a copy to avoid mutating the DB object directly if not intended to persist
                # But here we want to return enriched data.
                # Since exercises_json is a mutable JSON type in SQLAlchemy, modifying it might mark it dirty.
                # However, for the response, we just need the data.
                new_exercises = []
                for ex in circuit.exercises_json:
                    if isinstance(ex, dict):
                        ex_copy = ex.copy()
                        mid = ex_copy.get("movement_id")
                        if mid and mid in movements and not ex_copy.get("movement_name"):
                            ex_copy["movement_name"] = movements[mid]
                        new_exercises.append(ex_copy)
                circuit.exercises_json = new_exercises

    return circuits


@router.get("/{circuit_id}", response_model=CircuitTemplateResponse)
async def get_circuit(
    circuit_id: int,
    db: AsyncSession = Depends(get_db),
):
    circuit = await db.get(CircuitTemplate, circuit_id)
    if not circuit:
        raise HTTPException(status_code=404, detail="Circuit not found")
        
    # Enrich exercises_json with movement names
    if circuit.exercises_json:
        movement_ids = set()
        for ex in circuit.exercises_json:
            if isinstance(ex, dict) and ex.get("movement_id"):
                movement_ids.add(ex["movement_id"])
        
        if movement_ids:
            movements_result = await db.execute(select(Movement).where(Movement.id.in_(movement_ids)))
            movements = {m.id: m.name for m in movements_result.scalars().all()}
            
            new_exercises = []
            for ex in circuit.exercises_json:
                if isinstance(ex, dict):
                    ex_copy = ex.copy()
                    mid = ex_copy.get("movement_id")
                    if mid and mid in movements and not ex_copy.get("movement_name"):
                        ex_copy["movement_name"] = movements[mid]
                    new_exercises.append(ex_copy)
            circuit.exercises_json = new_exercises
            
    return circuit


@router.get("/admin/{circuit_id}", response_model=CircuitTemplateAdminDetail)
async def get_circuit_admin(
    circuit_id: int,
    db: AsyncSession = Depends(get_db),
    admin: bool = Depends(require_admin),
):
    circuit = await db.get(CircuitTemplate, circuit_id)
    if not circuit:
        raise HTTPException(status_code=404, detail="Circuit not found")
        
    # Enrich exercises_json
    enriched_exercises = []
    if circuit.exercises_json:
        movement_ids = set()
        for ex in circuit.exercises_json:
            if isinstance(ex, dict) and ex.get("movement_id"):
                movement_ids.add(ex["movement_id"])
        
        movements = {}
        if movement_ids:
            movements_result = await db.execute(select(Movement).where(Movement.id.in_(movement_ids)))
            movements = {m.id: m.name for m in movements_result.scalars().all()}
            
        for ex in circuit.exercises_json:
            if isinstance(ex, dict):
                ex_copy = ex.copy()
                mid = ex_copy.get("movement_id")
                if mid and mid in movements and not ex_copy.get("movement_name"):
                    ex_copy["movement_name"] = movements[mid]
                enriched_exercises.append(ex_copy)
    else:
        enriched_exercises = []

    raw_workout = load_raw_workout_for_circuit(circuit.name)
    return CircuitTemplateAdminDetail(
        id=circuit.id,
        name=circuit.name,
        description=circuit.description,
        circuit_type=circuit.circuit_type,
        exercises_json=enriched_exercises,
        default_rounds=circuit.default_rounds,
        default_duration_seconds=circuit.default_duration_seconds,
        tags=circuit.tags or [],
        difficulty_tier=circuit.difficulty_tier,
        raw_workout=raw_workout,
    )


@router.put("/admin/{circuit_id}", response_model=CircuitTemplateResponse)
async def update_circuit_admin(
    circuit_id: int,
    payload: CircuitTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    admin: bool = Depends(require_admin),
):
    circuit = await db.get(CircuitTemplate, circuit_id)
    if not circuit:
        raise HTTPException(status_code=404, detail="Circuit not found")
    circuit.exercises_json = payload.exercises_json
    await db.commit()
    await db.refresh(circuit)
    return circuit
