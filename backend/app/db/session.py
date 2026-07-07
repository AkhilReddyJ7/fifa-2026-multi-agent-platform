from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()

# SQLite (used by CI's in-memory DATABASE_URL) runs on a StaticPool that
# rejects the QueuePool sizing arguments Postgres uses.
_pool_kwargs = (
    {}
    if settings.database_url.startswith("sqlite")
    else {"pool_size": 10, "max_overflow": 20, "pool_pre_ping": True}
)

engine = create_async_engine(
    settings.database_url,
    echo=settings.app_debug,
    **_pool_kwargs,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncSession:  # type: ignore[return]
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
