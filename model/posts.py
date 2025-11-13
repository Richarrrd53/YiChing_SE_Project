from psycopg_pool import AsyncConnectionPool #使用connection 
from psycopg.rows import dict_row


async def get_projects_client(conn, id):
	async with conn.cursor(row_factory=dict_row) as cur:
		sql="""
            SELECT
				client.username, 
    			p.status, 
       			p.user_id,
          		p.id, 
            	p.title, 
             	p.create_time, 
              	p.deadline, 
               	p.budget
            FROM posts AS p
            JOIN users AS client ON p.user_id = client.id
            WHERE p.user_id = %s AND p.is_deleted = FALSE
            ORDER BY p.id DESC;
        """
		await cur.execute(sql, (id,))
		rows = await cur.fetchall()
		return rows

async def read_project(conn, id):
	async with conn.cursor() as cur:
		sql = """
            SELECT 
                p.id, 
                p.title, 
                p.content, 
                p.budget, 
                p.create_time, 
                p.deadline, 
                p.status,
                p.delivery_file_path,
                client.username AS client_username,
                freelancer.username AS accepted_freelancer_username 
            FROM posts AS p
            
            JOIN users AS client ON p.user_id = client.id
            
            LEFT JOIN users AS freelancer ON p.accepted_freelancer_id = freelancer.id
            
            WHERE p.id = %s AND p.is_deleted = FALSE;
        """
		await cur.execute(sql,(id,))
		row = await cur.fetchone()
		return row

async def get_any_project(conn, id):
	async with conn.cursor() as cur:
		sql = """
            SELECT 
                p.id, 
                p.title, 
                p.content, 
                p.budget, 
                p.create_time, 
                p.deadline, 
                p.status,
                p.delivery_file_path,
                client.username AS client_username,
                client.id AS user_id,
                freelancer.username AS accepted_freelancer_username 
            FROM posts AS p
            
            JOIN users AS client ON p.user_id = client.id
            
            LEFT JOIN users AS freelancer ON p.accepted_freelancer_id = freelancer.id
            
            WHERE p.id = %s
        """
		await cur.execute(sql,(id,))
		row = await cur.fetchone()
		return row

async def delete_project(conn, id):
	async with conn.cursor() as cur:
		sql="UPDATE posts SET is_deleted = TRUE WHERE id = %s;"
		sql2 = "UPDATE posts SET status = 'deleted' WHERE id = %s"
		await cur.execute(sql,(id,))
		await cur.execute(sql2,(id,))
		return True

async def get_history_project(conn, id, role):
	async with conn.cursor(row_factory=dict_row) as cur:
		if role == 'client':
			sql="""
				SELECT
					client.username, 
					p.status, 
					p.user_id,
					p.id, 
					p.title, 
					p.create_time, 
					p.deadline, 
					p.budget 
				FROM posts AS p
				JOIN users AS client ON p.user_id = client.id
				WHERE p.user_id = %s
				ORDER BY p.id DESC;
				"""
		else:
			sql="""
					SELECT 
					p.id, 
					p.title, 
					p.budget, 
					p.create_time, 
					p.deadline,
					p.status,
					u.username AS client_username 
				FROM posts AS p

				INNER JOIN users AS u ON p.user_id = u.id

				WHERE p.accepted_freelancer_id = %s
				ORDER BY p.create_time DESC;
				"""
		await cur.execute(sql, (id,))
		rows = await cur.fetchall()
		return rows

async def create_project(conn, title, content, budget, create_time, deadline, user_id):
	async with conn.cursor() as cur:
		sql="INSERT INTO posts (title, content, budget, create_time, deadline, user_id) values (%s,%s,%s,%s,%s,%s);"
		await cur.execute(sql,(title, content, budget, create_time, deadline, user_id))
		return True

async def restore_project(conn, project_id, today):
	async with conn.cursor() as cur:
		sql = "UPDATE posts SET is_deleted = FALSE WHERE id = %s;"
		sql2 = "UPDATE posts SET status = 'open' WHERE id = %s;"
		sql3 = "UPDATE posts SET create_time = %s WHERE id = %s;"
		await cur.execute(sql, (project_id,))
		await cur.execute(sql2, (project_id,))
		await cur.execute(sql3, (today,project_id))
		return True

async def edit_project(conn, id, title, content, budget, deadline):
	async with conn.cursor() as cur:
		sql1= "update posts set title = %s where id = %s;"
		sql2= "update posts set content = %s where id = %s;"
		sql3= "update posts set budget = %s where id = %s;"
		sql4= "update posts set deadline = %s where id = %s;"
		await cur.execute(sql1,(title,id))
		await cur.execute(sql2,(content,id))
		await cur.execute(sql3,(budget,id))
		await cur.execute(sql4,(deadline,id))
		return True

async def get_projects_by_freelancer(conn, freelancer_id):
    async with conn.cursor(row_factory=dict_row) as cur:
        sql = """
            SELECT 
                p.id, 
                p.title, 
                p.budget, 
                p.create_time, 
                p.deadline,
                p.status,
                u.username AS client_username 
            FROM posts AS p
            
            INNER JOIN users AS u ON p.user_id = u.id
            
            WHERE p.accepted_freelancer_id = %s AND p.is_deleted = FALSE
            ORDER BY p.create_time DESC;
        """
        await cur.execute(sql, (freelancer_id,))
        rows = await cur.fetchall()
        return rows


async def get_open_projects(conn):
    async with conn.cursor(row_factory=dict_row) as cur:
        sql = """
        	SELECT 
         		p.id, 
           		p.title, 
             	p.budget, 
              	p.create_time, 
               	p.deadline, 
                u.username AS client_username 
			FROM posts AS p 
			INNER JOIN users AS u ON p.user_id = u.id 
   			WHERE p.status = 'open' AND p.is_deleted = FALSE
      		ORDER BY p.create_time DESC; 
        
        """
        await cur.execute(sql)
        rows = await cur.fetchall()
        return rows
    
    
async def update_project_status_and_assignee(conn, project_id, status: str, freelancer_id):
    async with conn.cursor(row_factory=dict_row) as cur:
        sql = "UPDATE posts SET status = %s, accepted_freelancer_id = %s WHERE id = %s"
        await cur.execute(sql, (status, freelancer_id, project_id))
        return True

async def update_project_status(conn, project_id, status: str):
    async with conn.cursor() as cur:
        sql = "UPDATE posts SET status = %s WHERE id = %s"
        await cur.execute(sql, (status, project_id))

async def update_project_delivery(conn, project_id, file_path: str):
    async with conn.cursor() as cur:
        sql = "UPDATE posts SET status = 'delivered', delivery_file_path = %s WHERE id = %s AND status = 'in_progress' OR status = 'rejected'"
        await cur.execute(sql, (file_path, project_id))
        return True

