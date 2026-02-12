from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import NotFoundError

class BaseService:
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def _get_or_404[T](self, model: type[T], id: int, error_msg: str | None = None) -> T:
        result = await self._session.get(model, id)
        if not result:
            entity_name = model.__name__
            raise NotFoundError(
                entity_name,
                error_msg or f"{entity_name} {id} not found",
                {"id": id}
            )
        return result
