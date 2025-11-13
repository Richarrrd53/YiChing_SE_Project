from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row

DATABASE_URL = "postgresql://neondb_owner:npg_p6s8BQenCuxI@ep-little-brook-a1j52dfs-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"


_pool: AsyncConnectionPool | None = None

async def getDB():
    global _pool
    if _pool is None:
        _pool = AsyncConnectionPool(
            conninfo = DATABASE_URL,
            kwargs={"row_factory": dict_row},
            open= False
        )
        await _pool.open()
    async with _pool.connection() as conn:
        yield conn