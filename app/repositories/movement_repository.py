from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.movement import Movement
from app.repositories.base import Repository
from app.schemas.pagination import PaginationParams, PaginatedResult

class MovementRepository(Repository[Movement, int]):
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def get(self, id: int) -> Movement | None:
        result = await self._session.execute(
            select(Movement)
            .options(selectinload(Movement.movement_disciplines))
            .options(selectinload(Movement.movement_equipment))
            .options(selectinload(Movement.movement_tags))
            .where(Movement.id == id)
        )
        return result.scalar_one_or_none()
    
    async def list(self, filter: dict, pagination: PaginationParams) -> PaginatedResult[Movement]:
        query = select(Movement)
        
        if 'is_active' in filter:
            query = query.where(Movement.is_active == filter['is_active'])
        
        if 'pattern' in filter:
            query = query.where(Movement.pattern == filter['pattern'])
        
        query = query.order_by(Movement.created_at.desc())
        
        if pagination.cursor:
            from app.core.pagination import decode_cursor
            field, value = decode_cursor(pagination.cursor)
            if pagination.direction == "next":
                query = query.where(getattr(Movement, field) < value)
            else:
                query = query.where(getattr(Movement, field) > value)
        
        query = query.limit(pagination.limit + 1)
        result = await self._session.execute(query)
        items = result.scalars().all()
        
        has_more = len(items) > pagination.limit
        items = items[:pagination.limit]
        
        next_cursor = None
        if items and has_more:
            from app.core.pagination import encode_cursor
            next_cursor = encode_cursor(items[-1].created_at, "created_at")
        
        return PaginatedResult(items=items, next_cursor=next_cursor, has_more=has_more)
    
    async def create(self, entity: Movement) -> Movement:
        self._session.add(entity)
        await self._session.flush()
        return entity
    
    async def update(self, id: int, updates: dict) -> Movement | None:
        movement = await self.get(id)
        if movement:
            for key, value in updates.items():
                setattr(movement, key, value)
            await self._session.flush()
        return movement
    
    async def delete(self, id: int) -> bool:
        movement = await self.get(id)
        if movement:
            await self._session.delete(movement)
            return True
        return False
    
    async def list_by_ids(self, ids: list[int]) -> list[Movement]:
        """Fetch multiple movements by their IDs.
        
        Args:
            ids: List of movement IDs to fetch
            
        Returns:
            List of Movement objects (may include None for unfound IDs)
        """
        if not ids:
            return []
        
        result = await self._session.execute(
            select(Movement)
            .options(selectinload(Movement.movement_disciplines))
            .options(selectinload(Movement.movement_equipment))
            .options(selectinload(Movement.movement_tags))
            .where(Movement.id.in_(ids))
        )
        return list(result.scalars().all())
