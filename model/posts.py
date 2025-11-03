from psycopg_pool import AsyncConnectionPool #使用connection pool


async def getList(conn):
	async with conn.cursor() as cur:
		sql="select id,title from posts order by id desc;"
		await cur.execute(sql)
		rows = await cur.fetchall()
		return rows

async def getPost(conn, id):
	async with conn.cursor() as cur:
		sql="select id,title, content, filename from posts where id=%s;"
		await cur.execute(sql,(id,))
		row = await cur.fetchone()
		return row

async def deletePost(conn, id):
	async with conn.cursor() as cur:
		sql="delete from posts where id=%s;"
		await cur.execute(sql,(id,))
		return True

async def addPost(conn, title, content):
	async with conn.cursor() as cur:
		sql="insert into posts (title,content) values (%s,%s);"
		await cur.execute(sql,(title,content))
		return True

async def setUploadFile(conn, id, filename):
	async with conn.cursor() as cur:
		sql="update posts set filename=%s where id=%s;"
		await cur.execute(sql,(filename,id))
		return True


