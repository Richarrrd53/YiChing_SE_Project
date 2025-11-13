import psycopg
from psycopg.rows import dict_row

async def get_bids_for_project(conn, project_id):
    async with conn.cursor(row_factory=dict_row) as cur:
        sql="select b.id, b.bid_amount, b.message, b.created_at, b.status, u.username as freelancer_username, u.id as freelancer_id from bids as b join users as u on b.freelancer_id = u.id where b.project_id = %s order by b.bid_amount asc"
        await cur.execute(sql, (project_id,))
        rows = await cur.fetchall()
        return rows

async def check_bid(conn, project_id, freelancer_id):
    async with conn.cursor() as cur:
        sql_check = "SELECT 1 FROM bids WHERE project_id = %s AND freelancer_id = %s"
        await cur.execute(sql_check, (project_id, freelancer_id))
        if await cur.fetchone():
            return True
        else:
            return False

async def create_bid(conn, project_id, freelancer_id, bid_amount, message: str):
    async with conn.cursor(row_factory=dict_row) as cur:
        sql_check = "SELECT 1 FROM bids WHERE project_id = %s AND freelancer_id = %s"
        await cur.execute(sql_check, (project_id, freelancer_id))
        if await cur.fetchone():
            raise Exception("您已經對此專案報價")
        
        sql_insert = "INSERT INTO bids (project_id, freelancer_id, bid_amount, message, status) VALUES (%s, %s, %s, %s, 'pending')"
        await cur.execute(sql_insert, (project_id, freelancer_id, bid_amount, message))
        
async def get_bid_details(conn, bid_id):
    async with conn.cursor(row_factory=dict_row) as cur:
        sql = "SELECT project_id, freelancer_id FROM bids WHERE id = %s"
        await cur.execute(sql, (bid_id,))
        return await cur.fetchone()
    
async def get_bid_id(conn, project_id, freelancer_id):
    async with conn.cursor() as cur:
        sql = "SELECT id FROM bids WHERE project_id = %s AND freelancer_id = %s"
        await cur.execute(sql, (project_id ,freelancer_id,))
        return await cur.fetchone()

async def get_bid_status(conn, id):
    async with conn.cursor() as cur:
        sql = "SELECT status FROM bids WHERE id = %s"
        await cur.execute(sql, (id,))
        return await cur.fetchone()


async def set_bid_status(conn, bid_id, project_id, status: str):
    rejected_freelancer_ids = []
    async with conn.cursor(row_factory=dict_row) as cur:
        sql_accept = "UPDATE bids SET status = %s WHERE id = %s"
        await cur.execute(sql_accept, (status, bid_id))
        
        sql_reject = "UPDATE bids SET status = 'rejected' WHERE project_id = %s AND id != %s RETURNING freelancer_id"
        await cur.execute(sql_reject, (project_id, bid_id))
        rows = await cur.fetchall()
        rejected_freelancer_ids = [row['freelancer_id'] for row in rows]
    
    return rejected_freelancer_ids