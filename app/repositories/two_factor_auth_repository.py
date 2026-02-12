from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.two_factor_auth import TwoFactorAuth
from app.repositories.base import Repository
from app.schemas.pagination import PaginationParams, PaginatedResult


class TwoFactorAuthRepository(Repository[TwoFactorAuth, int]):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get(self, id: int) -> TwoFactorAuth | None:
        result = await self._session.execute(
            select(TwoFactorAuth).where(TwoFactorAuth.id == id)
        )
        return result.scalar_one_or_none()

    async def get_by_user_id(self, user_id: int) -> TwoFactorAuth | None:
        result = await self._session.execute(
            select(TwoFactorAuth)
            .where(TwoFactorAuth.user_id == user_id)
            .order_by(TwoFactorAuth.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list(self, filter: dict, pagination: PaginationParams) -> PaginatedResult[TwoFactorAuth]:
        query = select(TwoFactorAuth)
        
        if 'user_id' in filter:
            query = query.where(TwoFactorAuth.user_id == filter['user_id'])
        
        if 'is_enabled' in filter:
            query = query.where(TwoFactorAuth.is_enabled == filter['is_enabled'])
        
        query = query.order_by(TwoFactorAuth.created_at.desc())
        
        result = await self._session.execute(query.limit(pagination.limit + 1))
        items = result.scalars().all()
        
        has_more = len(items) > pagination.limit
        items = items[:pagination.limit]
        
        return PaginatedResult(items=items, next_cursor=None, has_more=has_more)

    async def create(self, entity: TwoFactorAuth) -> TwoFactorAuth:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def update(self, id: int, updates: dict) -> TwoFactorAuth | None:
        two_factor = await self.get(id)
        if two_factor:
            for key, value in updates.items():
                if hasattr(two_factor, key):
                    setattr(two_factor, key, value)
            await self._session.flush()
        return two_factor

    async def delete(self, id: int) -> bool:
        two_factor = await self.get(id)
        if two_factor:
            await self._session.delete(two_factor)
            return True
        return False
