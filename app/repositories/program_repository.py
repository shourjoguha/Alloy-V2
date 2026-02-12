from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, update
from sqlalchemy.orm import selectinload
from app.models.program import Program, Microcycle, Session, ProgramDiscipline
from app.models.user import UserProfile, User
from app.repositories.base import Repository
from app.schemas.pagination import PaginationParams, PaginatedResult

class ProgramRepository(Repository[Program, int]):
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def get(self, id: int) -> Program | None:
        result = await self._session.execute(
            select(Program)
            .options(selectinload(Program.program_disciplines))
            .options(selectinload(Program.microcycles))
            .where(Program.id == id)
        )
        return result.scalar_one_or_none()
    
    async def list(self, filter: dict, pagination: PaginationParams) -> PaginatedResult[Program]:
        query = select(Program)
        
        if 'user_id' in filter:
            query = query.where(Program.user_id == filter['user_id'])
        
        if 'is_active' in filter:
            query = query.where(Program.is_active == filter['is_active'])
        
        query = query.order_by(Program.created_at.desc())
        
        if pagination.cursor:
            from app.core.pagination import decode_cursor
            field, value = decode_cursor(pagination.cursor)
            if pagination.direction == "next":
                query = query.where(getattr(Program, field) < value)
            else:
                query = query.where(getattr(Program, field) > value)
        
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
    
    async def create(self, entity: Program) -> Program:
        self._session.add(entity)
        await self._session.flush()
        return entity
    
    async def update(self, id: int, updates: dict) -> Program | None:
        program = await self.get(id)
        if program:
            for key, value in updates.items():
                setattr(program, key, value)
            await self._session.flush()
        return program
    
    async def delete(self, id: int) -> bool:
        program = await self.get(id)
        if program:
            await self._session.delete(program)
            return True
        return False

    async def get_user_profile(self, user_id: int) -> UserProfile | None:
        result = await self._session.execute(
            select(UserProfile).where(UserProfile.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_user(self, user_id: int) -> User | None:
        result = await self._session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def deactivate_other_programs(self, user_id: int, exclude_program_id: int) -> None:
        await self._session.execute(
            update(Program).where(
                and_(
                    Program.user_id == user_id,
                    Program.is_active == True,
                    Program.id != exclude_program_id
                )
            ).values(is_active=False)
        )

    async def get_program_by_id_and_user(self, program_id: int, user_id: int) -> Program | None:
        result = await self._session.execute(
            select(Program).where(
                and_(
                    Program.id == program_id,
                    Program.user_id == user_id
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_microcycle(self, microcycle_id: int) -> Microcycle | None:
        result = await self._session.execute(
            select(Microcycle).where(Microcycle.id == microcycle_id)
        )
        return result.scalar_one_or_none()

    async def list_sessions_by_microcycle(self, microcycle_id: int) -> list[Session]:
        result = await self._session.execute(
            select(Session).where(Session.microcycle_id == microcycle_id)
        )
        return list(result.scalars().all())

    async def get_session(self, session_id: int) -> Session | None:
        result = await self._session.execute(
            select(Session).where(Session.id == session_id)
        )
        return result.scalar_one_or_none()

    async def list_active_programs_by_user(self, user_id: int) -> list[Program]:
        result = await self._session.execute(
            select(Program).where(
                and_(
                    Program.user_id == user_id,
                    Program.is_active == True
                )
            )
        )
        return list(result.scalars().all())

    def add(self, entity) -> None:
        self._session.add(entity)

    async def flush(self) -> None:
        await self._session.flush()

    async def add_program_discipline(self, program_id: int, discipline_type: str, weight: int) -> ProgramDiscipline:
        discipline = ProgramDiscipline(
            program_id=program_id,
            discipline_type=discipline_type,
            weight=weight,
        )
        self._session.add(discipline)
        return discipline

    async def add_microcycle(self, microcycle: Microcycle) -> Microcycle:
        self._session.add(microcycle)
        await self._session.flush()
        return microcycle

    async def add_session(self, session: Session) -> Session:
        self._session.add(session)
        return session

    async def commit(self) -> None:
        await self._session.commit()

    async def refresh(self, entity) -> None:
        await self._session.refresh(entity)
