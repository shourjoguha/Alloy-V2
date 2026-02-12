from functools import wraps
from typing import Callable, ParamSpec, TypeVar
from sqlalchemy.ext.asyncio import AsyncSession

P = ParamSpec('P')
T = TypeVar('T')


def transactional(
    *,
    timeout: float | None = None,
    readonly: bool = False,
):
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            session = _extract_session(args, kwargs)
            
            async with session.begin():
                return await func(*args, **kwargs)
        return wrapper
    return decorator


def _extract_session(args, kwargs) -> AsyncSession:
    if args and isinstance(args[0], AsyncSession):
        return args[0]
    if 'db' in kwargs:
        return kwargs['db']
    if 'session' in kwargs:
        return kwargs['session']
    if args and hasattr(args[0], '_session') and isinstance(args[0]._session, AsyncSession):
        return args[0]._session
    raise ValueError("No session found in function arguments")
