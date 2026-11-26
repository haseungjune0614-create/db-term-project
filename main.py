"""서버 시작점.  실행:  uvicorn main:app --reload
브라우저에서 http://127.0.0.1:8000 접속

각자 기능은 routers/ 같은 별도 파일로 만들어서 아래에 include_router 로 붙이기 (충돌 방지)
"""
import os

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.auth import current_user_id
from app.db import query_one

load_dotenv()

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY", "dev-secret"))
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/")
def index(request: Request):
    # DB 연결 확인용 첫 화면
    row = query_one("SELECT COUNT(*) AS n FROM users")
    return templates.TemplateResponse(
        request,
        "index.html",
        {"user_count": row["n"], "me": current_user_id(request)},
    )


# 예시: 기능 파일을 만들면 이렇게 붙이기
# from routers import auth_routes, post_routes, follow_routes
# app.include_router(auth_routes.router)
# app.include_router(post_routes.router)
# app.include_router(follow_routes.router)
