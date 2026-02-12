from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
from app.models.program import Session, SessionExercise
from app.repositories.base import Repository
from app.schemas.pagination import PaginationParams, PaginatedResult
from app.core.pagination import decode_cursor, encode_cursor


class SessionRepository(Repository[Session, int]):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get(self, id: int) -> Session | None:
        result = await self._session.execute(
            select(Session)
            .options(selectinload(Session.exercises).selectinload(SessionExercise.movement))
            .options(selectinload(Session.microcycle))
            .where(Session.id == id)
        )
        return result.scalar_one_or_none()

    async def get_by_date(self, user_id: int, date) -> Session | None:
        result = await self._session.execute(
            select(Session)
            .options(selectinload(Session.exercises).selectinload(SessionExercise.movement))
            .where(
                and_(
                    Session.user_id == user_id,
                    Session.date == date
                )
            )
        )
        return result.scalar_one_or_none()

    async def list(self, filter: dict, pagination: PaginationParams) -> PaginatedResult[Session]:
        query = select(Session)

        if 'user_id' in filter:
            query = query.where(Session.user_id == filter['user_id'])
        
        if 'microcycle_id' in filter:
            query = query.where(Session.microcycle_id == filter['microcycle_id'])
        
        if 'session_type' in filter:
            query = query.where(Session.session_type == filter['session_type'])
        
        if 'start_date' in filter:
            query = query.where(Session.date >= filter['start_date'])
        
        if 'end_date' in filter:
            query = query.where(Session.date <= filter['end_date'])

        query = query.order_by(Session.date.desc(), Session.day_number.desc())
        
        if pagination.cursor:
            field, value = decode_cursor(pagination.cursor)
            if pagination.direction == "next":
                query = query.where(getattr(Session, field) < value)
            else:
                query = query.where(getattr(Session, field) > value)
        
        query = query.limit(pagination.limit + 1)
        result = await self._session.execute(query)
        items = result.scalars().all()
        
        has_more = len(items) > pagination.limit
        items = items[:pagination.limit]
        
        next_cursor = None
        if items and has_more:
            next_cursor = encode_cursor(items[-1].date, "date")
        
        return PaginatedResult(items=items, next_cursor=next_cursor, has_more=has_more)

    async def list_by_microcycle(self, microcycle_id: int) -> list[Session]:
        result = await self._session.execute(
            select(Session)
            .options(selectinload(Session.exercises).selectinload(SessionExercise.movement))
            .where(Session.microcycle_id == microcycle_id)
            .order_by(Session.day_number)
        )
        return list(result.scalars().all())

    async def create(self, entity: Session) -> Session:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def update(self, id: int, updates: dict) -> Session | None:
        session = await self.get(id)
        if session:
            for key, value in updates.items():
                if hasattr(session, key):
                    setattr(session, key, value)
            await self._session.flush()
        return session

    async def delete(self, id: int) -> bool:
        session = await self.get(id)
        if session:
            await self._session.delete(session)
            return True
        return False

    async def count_by_user(self, user_id: int, start_date=None, end_date=None) -> int:
        query = select(Session).where(Session.user_id == user_id)
        
        if start_date:
            query = query.where(Session.date >= start_date)
        if end_date:
            query = query.where(Session.date <= end_date)
        
        from sqlalchemy import func
        result = await self._session.execute(select(func.count()).select_from(query))
        return result.scalar()
