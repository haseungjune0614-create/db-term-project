"""서버 시작점.  실행:  uvicorn main:app --reload
브라우저에서 http://127.0.0.1:8000 접속

[전체 구조 요약]
- FastAPI 앱 생성 및 세션 미들웨어(로그인 유지용 쿠키) 등록
- 정적 파일 폴더(static/) 및 업로드 이미지 폴더(static/uploads/) 마운트
- 4개의 기능별 라우터(회원, 프로필/팔로우, 게시물/피드/댓글/좋아요, 메시지) 연결
"""
import os

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.auth import current_user_id
from routers import auth_routes, message_routes, post_routes, profile_routes

# .env 파일에서 DB 비밀번호, SECRET_KEY 등 환경변수 로드
load_dotenv()

# 업로드 이미지를 저장할 로컬 폴더가 없으면 자동 생성
os.makedirs("static/uploads", exist_ok=True)

app = FastAPI()

# 브라우저 쿠키에 로그인 세션(user_id)을 서명·암호화하여 저장하는 미들웨어
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY", "dev-secret"))

# 정적 파일 및 업로드 이미지 URL 매핑
# DB의 posts.image_path('/uploads/파일명')가 실제 static/uploads/파일명으로 서빙됨
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory="static/uploads"), name="uploads")


@app.get("/")
def index(request: Request):
    """루트 접속 시: 로그인 상태면 홈 피드(/feed), 비로그인 상태면 로그인(/login)으로 이동"""
    if current_user_id(request):
        return RedirectResponse("/feed", status_code=303)
    return RedirectResponse("/login", status_code=303)


# 기능별로 분리된 라우터를 메인 앱에 등록
app.include_router(auth_routes.router)      # 회원가입, 로그인/로그아웃, 비밀번호 변경
app.include_router(profile_routes.router)   # 프로필 조회, 팔로우/언팔로우, 팔로워/팔로잉 목록
app.include_router(post_routes.router)      # 홈 피드, 사진 업로드, 게시물 상세, 댓글(@멘션), 좋아요
app.include_router(message_routes.router)   # 1:1 메시지(DM) 목록, 채팅 내역, 전송
