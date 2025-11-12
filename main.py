# main.py
from fastapi import FastAPI, Depends, Request, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse,RedirectResponse

from fastapi.templating import Jinja2Templates
templates = Jinja2Templates(directory="templates")

from routes.upload import router as upload_router
from routes.dbQuery import router as db_router
from model.db import getDB
import model.posts as posts
import model.users as users
import security


# Include the router
app = FastAPI()
#prefix will be prepended before the route
app.include_router(upload_router, prefix="/api") 
app.include_router(db_router, prefix="/api")

#use session middleware for session mamagement
from starlette.middleware.sessions import SessionMiddleware
app.add_middleware(
    SessionMiddleware,
    secret_key="yiching1218",
	max_age=None, #86400,  # 1 day
    same_site="lax",  # Options: 'lax', 'strict', 'none'
    https_only=False,  # Set to True in production with HTTPS,
)

#example of using dependency function for login check
def get_current_user(request: Request):
	user_id = request.session.get("user")
	#for not-login user, user_id will be None
	return user_id

def get_current_role(request: Request):
	return request.session.get("role")
	
#example of using function wrapper to check role
def checkRole(requiredRole:str):
	def checker(request: Request):
		user_role = request.session.get("role")
		if user_role == requiredRole:
			return True
		else:
			raise HTTPException(status_code=401, detail="Not authenticated")
	return checker
	

@app.get("/")
async def root(request:Request,conn=Depends(getDB),user:str=Depends(get_current_user)):
	if user is None:
		return RedirectResponse(url="/loginForm.html", status_code=302)

	myRole = get_current_role(request)
	myList= await posts.getList(conn)
	#return templates.TemplateResponse("home.html", {"request":request})
	return RedirectResponse(url="/homeVue.html", status_code=302)
	#return templates.TemplateResponse("postList.html", {"request":request,"items": myList,"role": myRole})

@app.get("/readList")
async def root(request:Request,conn=Depends(getDB),user:str=Depends(get_current_user)):
	myRole = get_current_role(request)
	myList= await posts.getList(conn)
	return templates.TemplateResponse("postList.html", {"request":request,"items": myList,"role": myRole})


@app.get("/read/{id}")
async def readPost(request:Request, id:int,conn=Depends(getDB)):
	postDetail = await posts.getPost(conn,id)
	return templates.TemplateResponse("postDetail.html", {"request":request,"post": postDetail})

@app.get("/delete/{id}")
#only admin can call this
async def delPost(request:Request, id:int,conn=Depends(getDB),role=Depends(checkRole("admin"))):
	await posts.deletePost(conn,id)
	return RedirectResponse(url="/readList", status_code=302)

@app.post("/addPost")
async def addPost(
	request:Request,
	title: str=Form(...),
	content:str=Form(...),
	conn=Depends(getDB)
	):

	postDetail = await posts.addPost(conn,title,content)
	return RedirectResponse(url="/readList", status_code=302)

@app.get("/logout")
async def logout(request: Request):
	request.session.clear()
	return RedirectResponse(url="/loginForm.html")

@app.post("/login") #receive login data from form post
async def login(
	req: Request,
	username: str = Form(...),
	password: str = Form(...),
	conn = Depends(getDB)
):
	password = password.strip()
	user_from_db = await users.get_user_by_username(conn, username)

	if not user_from_db:
		req.session.clear()
		return HTMLResponse("使用者不存在，<a href='/loginForm.html'>再試一次</a>", status_code=401)
	
	is_password_correct = security.verify_pwd(password, user_from_db["hashed_password"])
	print(is_password_correct)

	if not is_password_correct:
		req.session.clear()
		return HTMLResponse("密碼錯誤，<a href='/loginForm.html'>再試一次</a>", status_code=401)
	
	req.session["user"] = user_from_db["username"]
	req.session["role"] = user_from_db["role"]

	if user_from_db["role"] == "client":
		print(f"{username} 已登入，登入身分：委託人")
	else:
		print(f"{username} 已登入，登入身分：接案人")
		
	
	return RedirectResponse(url="/", status_code=302)

@app.post("/regist")
async def registUser(req: Request, conn=Depends(getDB), username: str=Form(...), password: str=Form(...), role: str=Form(...)):
	exsiting_user = await users.get_user_by_username(conn, username)
	if exsiting_user:
		return HTMLResponse("此使用者已註冊過，<a href='/loginForm.html'>立刻登入</a>", status_code=401)

	if role not in ['client', 'freelancer']:
		return HTMLResponse("身分錯誤，<a href='/regist.html'>再試一次</a>", status_code=401)
	
	hashed_password = security.get_pwd_hash(password)

	try:
		await users.create_user(conn, username, hashed_password, role)
		return HTMLResponse("註冊成功，<a href='/loginForm.html'>立刻登入</a>", status_code=401)
	except Exception as e:
		print(f": {e}")
		return HTMLResponse("註冊失敗，<a href='/regist.html'>再試一次</a>", status_code=401)


@app.get("/getPostsJson")
async def getPostsJson(request:Request,conn=Depends(getDB)):
	myList= await posts.getList(conn)
	return myList

@app.get("/readPostJson/{id}")
async def readPostJson(request:Request, id:int,conn=Depends(getDB)):
	postDetail = await posts.getPost(conn,id)
	return postDetail

app.mount("/", StaticFiles(directory="www"))