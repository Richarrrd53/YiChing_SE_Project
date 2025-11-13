# main.py
from fastapi import FastAPI, Depends, Request, Form, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse,RedirectResponse

from fastapi.templating import Jinja2Templates
templates = Jinja2Templates(directory="templates")

from routes.upload import router as upload_router
from routes.dbQuery import router as db_router
from model.db import getDB
import model.posts as posts
import model.users as users
import model.bids as bids
import security

from datetime import date
from datetime import timedelta

import os
import re

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
    username = request.session.get("user")
    #for not-login user, user_id will be None
    return username

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

def safeFilename(filename:str):
    ALLOWED_EXTENSIONS = {".txt", ".pdf", ".png", ".jpg", ".jpeg", ".zip", ".rar", ".ai"}
    name, ext = os.path.splitext(filename)

    if ext.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f": {', '.join(ALLOWED_EXTENSIONS)}"
        )
    safe = re.sub(r'[<>:"/\\|?*\x00-\x1F]', '_', filename)
    safe = re.sub(r'_+', '_', safe)
    return safe[:255]

def translate_status_text(status):
    status_maps={
        "open": "開放中",
        "in_progress": "進行中",
        "delivered": "已交付",
        "deleted": "已刪除",
        "rejected": "已退件",
        "completed": "已結案"
    }
    return status_maps.get(status, "未知")

@app.get("/")
async def roots(request:Request,conn=Depends(getDB),username:str=Depends(get_current_user)):
    if username is None:
        return RedirectResponse(url="/login.html", status_code=302)
        
    user = await users.get_user_by_username(conn, username)
    
    myRole = get_current_role(request)
    if myRole == 'client':
        myList= await posts.get_projects_client(conn, user['id'])
        for item in myList:
            item["status_text"] = translate_status_text(item['status'])
            item["deadline_date"] = item["create_time"] + timedelta(item['deadline'])
    else:
        myList = await posts.get_open_projects(conn)
        for item in myList:
            item["deadline_date"] = item["create_time"] + timedelta(item['deadline'])
    
    
    return templates.TemplateResponse("projects_list.html", {"request":request,"items": myList,"role": myRole, "username": username})

@app.get("/page/create-project")
async def create_project_page(req: Request):
    return templates.TemplateResponse("create_project_form.html", {"request":req})

@app.post("/create-project")
async def create_project(
    req:Request,
    user_name: str = Depends(get_current_user),
    title: str=Form(...),
    content:str=Form(...),
    budget:int=Form(...),
    deadline:int=Form(...),
    conn=Depends(getDB)
    ):
    if user_name is None:
        return templates.TemplateResponse("error.html", {"request": req, "message": "密碼錯誤", "back_link": "/login.html", "back_text": "再試一次"}, status_code=401)
    try:
        today = date.today()

        user = await users.get_user_by_username(conn, user_name)
        if not user:
            raise HTTPException(status_code=404, detail="找不到使用者")
        
        user_id = user['id']

        await posts.create_project(conn, title, content, budget, today, deadline, user_id)

        return RedirectResponse(url="/", status_code=302)
    
    except Exception as e:
        print(f"建立專案時發生錯誤: {e}")
        return templates.TemplateResponse("error.html", {"request": req, "message": f"建立專案時發生錯誤: {e}", "back_link": "/page/create-project", "back_text": "再試一次"}, status_code=401)


@app.get("/page/read/{id}")
async def read_project(request:Request, id:int ,conn=Depends(getDB), username = Depends(get_current_user)):
    project = await posts.read_project(conn,id)
    project["deadline_date"] = project["create_time"] + timedelta(project["deadline"])
    project["status_text"] = translate_status_text(project["status"])
    role = get_current_role(request)
    if role == 'freelancer':
        freelancer_id = await users.get_user_by_username(conn, username)
        is_bid_exist = await bids.check_bid(conn, id, freelancer_id['id'])
        if is_bid_exist:
            bid_id = await bids.get_bid_id(conn, id, freelancer_id['id'])
            get_bid_status = await bids.get_bid_status(conn, bid_id['id'])
            bid_status = get_bid_status['status']
        else:
            bid_status = ""
        return templates.TemplateResponse("read_project.html", {"request":request,"project": project, "role": role, "is_bid_exist": is_bid_exist, "bid_status": bid_status})
    else:
        bids_list = await bids.get_bids_for_project(conn, id)
        return templates.TemplateResponse("read_project.html", {"request":request,"project": project, "role": role, "bids": bids_list})

@app.get("/bids/accept/{id}")
async def accept_bid(req: Request, id: int, conn = Depends(getDB)):
    bid = await bids.get_bid_details(conn, id)
    freelancer_id = bid['freelancer_id']
    project_id = bid['project_id']
    await bids.set_bid_status(conn, id, project_id, 'accepted')
    await posts.update_project_status_and_assignee(conn, project_id, "in_progress", freelancer_id)
    return RedirectResponse(url=f"/page/read/{project_id}", status_code=302)

@app.get("/page/check-delete/{id}")
async def check_delete(req: Request, id: int, conn = Depends(getDB)):
    project = await posts.read_project(conn,id)
    return templates.TemplateResponse("check_delete.html", {"request":req,"project": project})


@app.get("/delete-project/{id}")
async def delete_project(req: Request, id: int, conn = Depends(getDB), username=Depends(get_current_user)):
    user_id = await users.get_user_by_username(conn, username)
    project = await posts.get_any_project(conn,id)
    if user_id['id'] != project['user_id']:
        return templates.TemplateResponse("error.html", {"request": req, "message": "身分錯誤，權限不足", "back_link": "/", "back_text": "回首頁"}, status_code=401)
    await posts.delete_project(conn, id)
    return templates.TemplateResponse("success.html", {"request": req, "message": "專案已移至歷史封存", "back_link": "/", "back_text": "回首頁"}, status_code=200)

@app.get("/page/my-jobs")
async def my_jobs_list(req: Request, conn = Depends(getDB), username=Depends(get_current_user), role =Depends(get_current_role)):
    if role == 'client':
        return templates.TemplateResponse("error.html", {"request": req, "message": "登入身分錯誤", "back_link": "/", "back_text": "回首頁"}, status_code=401)
    user = await users.get_user_by_username(conn, username)
    user_id = user['id']
    project_list = await posts.get_projects_by_freelancer(conn, user_id)
    if project_list:
        for item in project_list:
            item["status_text"] = translate_status_text(item['status'])
            item["deadline_date"] = item["create_time"] + timedelta(item['deadline'])
            
    return templates.TemplateResponse("my_jobs_page.html", {"request":req,"username":username,"items": project_list, "role": role})
    

@app.get("/page/history")
async def history_page(req: Request, conn =Depends(getDB), username = Depends(get_current_user), role =Depends(get_current_role)):
    user_id = await users.get_user_by_username(conn, username)
    history_project = await posts.get_history_project(conn, user_id["id"], role)
    if history_project:
        for item in history_project:
            item["status_text"] = translate_status_text(item["status"])
            item["deadline_date"] = item["create_time"] + timedelta(item['deadline'])
    return templates.TemplateResponse("history_page.html", {"request":req,"items": history_project,"username":username, "role": role})

@app.get("/page/check-restore/{id}")
async def check_restore(req: Request, id: int, conn = Depends(getDB), role =Depends(get_current_role)):
    project = await posts.get_any_project(conn, id)
    return templates.TemplateResponse("check_restore.html", {"request":req,"project": project})

@app.get("/restore-project/{id}")
async def restore_project(req: Request, id: int, conn = Depends(getDB), username=Depends(get_current_user)):
    user_id = await users.get_user_by_username(conn, username)
    project = await posts.get_any_project(conn,id)
    if user_id['id'] != project['user_id']:
        return templates.TemplateResponse("error.html", {"request": req, "message": "身分錯誤，權限不足", "back_link": "/", "back_text": "回首頁"}, status_code=401)
    today = date.today()
    await posts.restore_project(conn, id, today)
    return templates.TemplateResponse("success.html", {"request": req, "message": "專案已成功復原", "back_link": "/page/history", "back_text": "返回歷史封存"}, status_code=200)

@app.get("/page/edit/{id}")
async def edit_project_page(req: Request, id: int, conn = Depends(getDB)):
    project = await posts.get_any_project(conn, id)
    project["deadline_date"] = project["create_time"] + timedelta(project["deadline"])
    project["status_text"] = translate_status_text(project["status"])
    return templates.TemplateResponse("edit_project_page.html", {"request":req,"project": project})

@app.post("/edit-project/{id}")
async def edit_project(req: Request, id: int, conn = Depends(getDB), title: str=Form(...), content :str = Form(...), budget: int=Form(...), deadline: int=Form(...)):
    await posts.edit_project(conn, id, title, content, budget, deadline)
    return templates.TemplateResponse("success.html", {"request": req, "message": "專案已編輯成功", "back_link": f"/page/read/{id}", "back_text": "返回專案"}, status_code=200)

@app.post("/submit-bid/{id}")
async def submit_bid(req: Request, id: int, conn = Depends(getDB), bid_amount: int=Form(...), message :str=Form(...), username = Depends(get_current_user)):
    user = await users.get_user_by_username(conn, username)
    try:
        await bids.create_bid(conn, id, user['id'], bid_amount, message)
        return templates.TemplateResponse("success.html", {"request": req, "message": "提案成功，請耐心等待委託人接受報價", "back_link": "/", "back_text": "回首頁"}, status_code=200)
    except Exception:
        return templates.TemplateResponse("error.html", {"request": req, "message": "錯誤：你已經提過報價，請勿重複提案", "back_link": "/", "back_text": "回首頁"}, status_code=400)

@app.post("/deliver-file/{id}", dependencies=[Depends(checkRole("freelancer"))])
async def deliver_file(req: Request,
    id: int,
    conn = Depends(getDB),
    user_name: str = Depends(get_current_user),
    delivery_file: UploadFile = File(...)
):
    if user_name is None:
        return templates.TemplateResponse("error.html", {"request": req, "message": "請先登入", "back_link": "/login.html", "back_text": "前往登入"}, status_code=401)

    try:
        project_detail = await posts.read_project(conn, id)

        if not project_detail:
            raise HTTPException(status_code=404, detail="找不到專案")
        
        if project_detail['accepted_freelancer_username'] != user_name:
            raise HTTPException(status_code=403, detail="您不是此專案的承接人")
        
        if project_detail['status'] != 'in_progress' and project_detail['status'] != 'rejected' :
            raise HTTPException(status_code=400, detail="此專案並非在可提交檔案狀態")
        
        if delivery_file.filename is None:
            raise HTTPException(status_code=400, detail="上傳的檔案缺少檔名")
        
        safe_name = safeFilename(delivery_file.filename)
        
        upload_dir = "www/uploads/deliveries"
        os.makedirs(upload_dir, exist_ok=True) 
        file_path_for_db = f"uploads/deliveries/{id}_{safe_name}"
        full_save_path = os.path.join(upload_dir, f"{id}_{safe_name}")

        with open(full_save_path, "wb") as buffer:
            buffer.write(await delivery_file.read())

        await posts.update_project_delivery(conn, id, file_path_for_db)
        await posts.update_project_status(conn, id, 'delivered')
        
        return templates.TemplateResponse("success.html", {"request": req, "message": "已成功上傳檔案，請耐心等待委託人審核", "back_link": f"/page/read/{id}", "back_text": "返回專案"}, status_code=200)
    except HTTPException as e:
        return templates.TemplateResponse("error.html", {"request": req, "message": f"錯誤：{e.detail}", "back_link": f"/page/read/{id}", "back_text": "回首頁"}, status_code=e.status_code)
    except Exception as e:
        await conn.rollback()
        print(f": {e}")
        return templates.TemplateResponse("error.html", {"request": req, "message": f"伺服器錯誤：{e}", "back_link": f"/page/read/{id}", "back_text": "回首頁"}, status_code=500)

@app.get("/reject-file/{id}")
async def reject_file(
    req: Request, 
    id: int, 
    conn = Depends(getDB), 
    user_name: str = Depends(get_current_user)
):
    if user_name is None:
        return templates.TemplateResponse("error.html", {"request": req, "message": "請先登入", "back_link": "/login.html", "back_text": "前往登入"}, status_code=401)
    try:
        project = await posts.read_project(conn, id)
        
        if not project or project['client_username'] != user_name:
            raise HTTPException(status_code=403, detail="您沒有權限執行此操作")
        if project['status'] != 'delivered':
            raise HTTPException(status_code=400, detail="此專案並非在『已交付』狀態")

        await posts.update_project_status(conn, id, 'rejected')
        return templates.TemplateResponse("success.html", {"request": req, "message": "專案已退件，請等待接案人重新上傳", "back_link": f"/page/read/{id}", "back_text": "返回專案"}, status_code=200)

    except HTTPException as e:
        return templates.TemplateResponse("error.html", {"request": req, "message": f"錯誤：{e.detail}", "back_link": f"/page/read/{id}", "back_text": "回首頁"}, status_code=e.status_code)
    except Exception as e:
        await conn.rollback()
        return templates.TemplateResponse("error.html", {"request": req, "message": f"伺服器錯誤：{e}", "back_link": f"/page/read/{id}", "back_text": "回首頁"}, status_code=500)

@app.get('/complete-project/{id}')
async def complete_project(
    req: Request, 
    id: int, 
    conn = Depends(getDB), 
    user_name: str = Depends(get_current_user)
):
    if user_name is None:
        return templates.TemplateResponse("error.html", {"request": req, "message": "請先登入", "back_link": "/login.html", "back_text": "前往登入"}, status_code=401)

    try:
        project = await posts.read_project(conn, id)
        if not project or project['client_username'] != user_name:
            raise HTTPException(status_code=403, detail="您沒有權限執行此操作")
        
        if project['status'] != 'delivered':
            raise HTTPException(status_code=400, detail="此專案並非在『已交付』狀態")

        await posts.update_project_status(conn, id, 'completed')
        
        return templates.TemplateResponse("success.html", {"request": req, "message": "恭喜！專案已結案", "back_link": f"/page/read/{id}", "back_text": "返回專案"}, status_code=200)
        
    except HTTPException as e:
        return templates.TemplateResponse("error.html", {"request": req, "message": f"錯誤：{e.detail}", "back_link": f"/page/read/{id}", "back_text": "回首頁"}, status_code=e.status_code)
    except Exception as e:
        await conn.rollback()
        return templates.TemplateResponse("error.html", {"request": req, "message": f"伺服器錯誤：{e}", "back_link": f"/page/read/{id}", "back_text": "回首頁"}, status_code=500)

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login.html")

@app.post("/login")
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
        return templates.TemplateResponse("login.html", {"request": req, "error": "使用者不存在，請再試一次"}, status_code=401)
    
    is_password_correct = security.verify_pwd(password, user_from_db["hashed_password"])
    print(is_password_correct)

    if not is_password_correct:
        req.session.clear()
        return templates.TemplateResponse("login.html", {"request": req, "error": "密碼錯誤，請再試一次"}, status_code=401)
    
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
        return templates.TemplateResponse("regist.html", {"request": req, "error": "此使用者已註冊過"}, status_code=400)

    if role not in ['client', 'freelancer']:
        return templates.TemplateResponse("regist.html", {"request": req, "error": "身分錯誤，請重新選擇"}, status_code=400)
    
    hashed_password = security.get_pwd_hash(password)

    try:
        await users.create_user(conn, username, hashed_password, role)
        return templates.TemplateResponse("success.html", {"request": req, "message": "註冊成功！", "back_link": "/login.html", "back_text": "立刻登入"}, status_code=200)
    except Exception as e:
        await conn.rollback()
        print(f": {e}")
        return templates.TemplateResponse("error.html", {"request": req, "message": f"註冊失敗：{e}", "back_link": "/regist.html", "back_text": "再試一次"}, status_code=500)


app.mount("/", StaticFiles(directory="www"))