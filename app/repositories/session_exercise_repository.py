from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
from app.models.program import SessionExercise
from app.repositories.base import Repository
from app.schemas.pagination import PaginationParams, PaginatedResult
from app.core.pagination import decode_cursor, encode_cursor


class SessionExerciseRepository(Repository[SessionExercise, int]):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get(self, id: int) -> SessionExercise | None:
        result = await self._session.execute(
            select(SessionExercise)
            .options(selectinload(SessionExercise.movement))
            .options(selectinload(SessionExercise.circuit))
            .where(SessionExercise.id == id)
        )
        return result.scalar_one_or_none()

    async def list_by_session(self, session_id: int) -> list[SessionExercise]:
        result = await self._session.execute(
            select(SessionExercise)
            .options(selectinload(SessionExercise.movement))
            .options(selectinload(SessionExercise.circuit))
            .where(SessionExercise.session_id == session_id)
            .order_by(SessionExercise.order_in_session)
        )
        return list(result.scalars().all())

    async def list(self, filter: dict, pagination: PaginationParams) -> PaginatedResult[SessionExercise]:
        query = select(SessionExercise)

        if 'session_id' in filter:
            query = query.where(SessionExercise.session_id == filter['session_id'])
        
        if 'movement_id' in filter:
            query = query.where(SessionExercise.movement_id == filter['movement_id'])
        
        if 'user_id' in filter:
            query = query.where(SessionExercise.user_id == filter['user_id'])
        
        if 'exercise_role' in filter:
            query = query.where(SessionExercise.exercise_role == filter['exercise_role'])

        query = query.order_by(SessionExercise.order_in_session)
        
        if pagination.cursor:
            field, value = decode_cursor(pagination.cursor)
            if pagination.direction == "next":
                query = query.where(getattr(SessionExercise, field) < value)
            else:
                query = query.where(getattr(SessionExercise, field) > value)
        
        query = query.limit(pagination.limit + 1)
        result = await self._session.execute(query)
        items = result.scalars().all()
        
        has_more = len(items) > pagination.limit
        items = items[:pagination.limit]
        
        next_cursor = None
        if items and has_more:
            next_cursor = encode_cursor(items[-1].order_in_session, "order_in_session")
        
        return PaginatedResult(items=items, next_cursor=next_cursor, has_more=has_more)

    async def create(self, entity: SessionExercise) -> SessionExercise:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def create_batch(self, exercises: list[SessionExercise]) -> list[SessionExercise]:
        self._session.add_all(exercises)
        await self._session.flush()
        return exercises

    async def update(self, id: int, updates: dict) -> SessionExercise | None:
        exercise = await self.get(id)
        if exercise:
            for key, value in updates.items():
                if hasattr(exercise, key):
                    setattr(exercise, key, value)
            await self._session.flush()
        return exercise

    async def delete(self, id: int) -> bool:
        exercise = await self.get(id)
        if exercise:
            await self._session.delete(exercise)
            return True
        return False

    async def delete_by_session(self, session_id: int) -> int:
        from sqlalchemy import delete, func
        stmt = delete(SessionExercise).where(SessionExercise.session_id == session_id)
        result = await self._session.execute(stmt)
        return result.rowcount
