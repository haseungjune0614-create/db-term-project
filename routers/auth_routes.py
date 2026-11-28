"""회원 관리 라우터: 회원가입, 로그인, 로그아웃, 비밀번호 변경

- 연동 테이블: users (user_id PK, password, display_name, created_at)
- 보안 처리:
  1) 모든 SQL은 %s 파라미터 바인딩 사용 (SQL Injection 방지)
  2) 신규 가입 및 비밀번호 변경 시 bcrypt 단방향 해싱 저장 (app/auth.py)
"""
import re

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth import check_password, current_user_id, hash_password, login_required
from app.db import execute, query_one

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/signup")
def signup_page(request: Request):
    """회원가입 폼 화면 (이미 로그인한 상태면 피드로 이동)"""
    if current_user_id(request):
        return RedirectResponse("/feed", status_code=303)
    return templates.TemplateResponse(
        request, "signup.html", {"me": None, "error": None}
    )


@router.post("/signup")
def signup_submit(
    request: Request,
    user_id: str = Form(""),
    display_name: str = Form(""),
    password: str = Form(""),
):
    """회원가입 처리: 입력값/형식 검증 -> 아이디 중복 확인 -> bcrypt 해싱 후 INSERT"""
    user_id = user_id.strip()
    display_name = display_name.strip()

    if not user_id or not display_name or not password:
        return templates.TemplateResponse(
            request,
            "signup.html",
            {"me": None, "error": "모든 항목을 입력해 주세요."},
        )

    # DB 스키마 users.user_id VARCHAR(30) 및 @멘션 정규식 호환을 위한 형식 검사
    if not re.match(r"^[A-Za-z0-9_]{1,30}$", user_id):
        return templates.TemplateResponse(
            request,
            "signup.html",
            {"me": None, "error": "아이디는 영문, 숫자, 밑줄(_)만 30자 이내로 입력해 주세요."},
        )

    # 아이디 중복 확인
    exists = query_one("SELECT COUNT(*) AS cnt FROM users WHERE user_id = %s", (user_id,))
    if exists["cnt"] > 0:
        return templates.TemplateResponse(
            request,
            "signup.html",
            {"me": None, "error": "이미 사용 중인 아이디입니다."},
        )

    # 비밀번호를 bcrypt로 해싱하여 users 테이블에 저장
    execute(
        "INSERT INTO users (user_id, password, display_name) VALUES (%s, %s, %s)",
        (user_id, hash_password(password), display_name),
    )
    return RedirectResponse("/login", status_code=303)


@router.get("/login")
def login_page(request: Request):
    """로그인 폼 화면"""
    if current_user_id(request):
        return RedirectResponse("/feed", status_code=303)
    return templates.TemplateResponse(
        request, "login.html", {"me": None, "error": None}
    )


@router.post("/login")
def login_submit(
    request: Request,
    user_id: str = Form(""),
    password: str = Form(""),
):
    """로그인 처리: DB에서 유저 조회 -> 비밀번호 검증 -> 세션 쿠키에 user_id 저장"""
    user = query_one(
        "SELECT user_id, password, display_name FROM users WHERE user_id = %s",
        (user_id.strip(),),
    )
    # check_password는 bcrypt 해시 검증과 샘플 데이터 평문 비밀번호 비교를 모두 지원
    if not user or not check_password(password, user["password"]):
        return templates.TemplateResponse(
            request,
            "login.html",
            {"me": None, "error": "아이디 또는 비밀번호가 올바르지 않습니다."},
        )

    # 세션에 로그인 사용자 ID 기록 후 홈 피드로 이동
    request.session["user_id"] = user["user_id"]
    return RedirectResponse("/feed", status_code=303)


@router.get("/logout")
def logout(request: Request):
    """로그아웃: 세션 쿠키 전체 초기화 후 로그인 화면으로 이동"""
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


@router.get("/password")
def password_page(request: Request):
    """비밀번호 변경 화면 (로그인 필수)"""
    redirect = login_required(request)
    if redirect:
        return redirect
    return templates.TemplateResponse(
        request,
        "password.html",
        {"me": current_user_id(request), "error": None, "message": None},
    )


@router.post("/password")
def password_submit(
    request: Request,
    current_password: str = Form(""),
    new_password: str = Form(""),
):
    """비밀번호 변경 처리: 현재 비밀번호 확인 -> 새 비밀번호 bcrypt 해싱 후 UPDATE"""
    redirect = login_required(request)
    if redirect:
        return redirect

    me = current_user_id(request)
    user = query_one(
        "SELECT user_id, password, display_name FROM users WHERE user_id = %s",
        (me,),
    )

    if not check_password(current_password, user["password"]):
        return templates.TemplateResponse(
            request,
            "password.html",
            {"me": me, "error": "현재 비밀번호가 일치하지 않습니다.", "message": None},
        )

    if not new_password.strip():
        return templates.TemplateResponse(
            request,
            "password.html",
            {"me": me, "error": "새 비밀번호를 입력해 주세요.", "message": None},
        )

    execute(
        "UPDATE users SET password = %s WHERE user_id = %s",
        (hash_password(new_password), me),
    )
    return templates.TemplateResponse(
        request,
        "password.html",
        {"me": me, "error": None, "message": "비밀번호가 변경되었습니다."},
    )
