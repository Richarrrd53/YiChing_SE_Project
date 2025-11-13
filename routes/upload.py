from fastapi import APIRouter,File, UploadFile, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse,RedirectResponse

import os
import re
import model.posts as posts
from model.db import getDB

router = APIRouter()

# @router.post("/upload")
# async def upload_file(
# 	uploadedFile: UploadFile = File(...), 
# 	msg:str=Form(...),
# 	conn=Depends(getDB) ):
	
# 	contents = await uploadedFile.read()
# 	with open(f"www/uploads/{uploadedFile.filename}", "wb") as f:
# 		f.write(contents)
# 	await posts.setUploadFile(conn, msg,uploadedFile.filename)
# 	return RedirectResponse(url=f"/read/{msg}", status_code=302)


def safeFilename(filename:str):
	ALLOWED_EXTENSIONS = {".txt", ".pdf", ".png", ".jpg", ".jpeg", ".ai"}
	name, ext = os.path.splitext(filename)

	if ext.lower() not in ALLOWED_EXTENSIONS:
		return False
	safe = re.sub(r'[<>:"/\\|?*\x00-\x1F]', '_', filename)
	safe = re.sub(r'_+', '_', safe)
	return safe[:255]

@router.post("/upload/chunked")
async def chunk_upload_file(fileField: UploadFile = File(...)):
	MAX_FILE_SIZE = 10 * 1024 * 1024
	CHUNK_SIZE = 1024 * 1024
	if not fileField.filename:
		raise HTTPException(status_code=400, detail="上傳的檔案缺少檔名")
	safeFn = safeFilename(fileField.filename)
	upload_path = f"uploads/{safeFn}"
	total_size = 0

	try:
		with open(upload_path, "wb") as buffer:
			while True:
				chunk = await fileField.read(CHUNK_SIZE)
				if not chunk:
					break
				total_size += len(chunk)
				if total_size > MAX_FILE_SIZE:
					buffer.close()
					os.remove(upload_path)
					raise HTTPException(status_code=413, detail="File too large")
				buffer.write(chunk)
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

	return {"filename": safeFn, "size_bytes": total_size}
