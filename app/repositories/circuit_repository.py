from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.circuit import CircuitTemplate
from app.repositories.base import Repository
from app.schemas.pagination import PaginationParams, PaginatedResult

class CircuitRepository(Repository[CircuitTemplate, int]):
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def get(self, id: int) -> CircuitTemplate | None:
        result = await self._session.execute(
            select(CircuitTemplate).where(CircuitTemplate.id == id)
        )
        return result.scalar_one_or_none()
    
    async def list(self, filter: dict, pagination: PaginationParams) -> PaginatedResult[CircuitTemplate]:
        query = select(CircuitTemplate)
        
        if 'circuit_type' in filter:
            query = query.where(CircuitTemplate.circuit_type == filter['circuit_type'])
        
        if 'difficulty_tier' in filter:
            query = query.where(CircuitTemplate.difficulty_tier == filter['difficulty_tier'])
        
        query = query.order_by(CircuitTemplate.id.desc())
        
        if pagination.cursor:
            from app.core.pagination import decode_cursor
            field, value = decode_cursor(pagination.cursor)
            if pagination.direction == "next":
                query = query.where(getattr(CircuitTemplate, field) < value)
            else:
                query = query.where(getattr(CircuitTemplate, field) > value)
        
        query = query.limit(pagination.limit + 1)
        result = await self._session.execute(query)
        items = result.scalars().all()
        
        has_more = len(items) > pagination.limit
        items = items[:pagination.limit]
        
        next_cursor = None
        if items and has_more:
            from app.core.pagination import encode_cursor
            next_cursor = encode_cursor(items[-1].id, "id")
        
        return PaginatedResult(items=items, next_cursor=next_cursor, has_more=has_more)
    
    async def create(self, entity: CircuitTemplate) -> CircuitTemplate:
        self._session.add(entity)
        await self._session.flush()
        return entity
    
    async def update(self, id: int, updates: dict) -> CircuitTemplate | None:
        circuit = await self.get(id)
        if circuit:
            for key, value in updates.items():
                setattr(circuit, key, value)
            await self._session.flush()
        return circuit
    
    async def delete(self, id: int) -> bool:
        circuit = await self.get(id)
        if circuit:
            await self._session.delete(circuit)
            return True
        return False
