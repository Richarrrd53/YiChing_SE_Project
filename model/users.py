import psycopg
from psycopg.rows import dict_row

async def get_user_by_username(conn, username: str):
    sql = "select username, hashed_password, role, id FROM users WHERE username = %s"
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(sql, (username,))
        user = await cur.fetchone()
        return user


async def create_user(conn, username: str, hashed_password: str, role: str):
    async with conn.cursor() as cur:
        sql = "insert into users (username, hashed_password, role) values (%s, %s, %s)"
        await cur.execute(sql, (username, hashed_password, role))
        return True