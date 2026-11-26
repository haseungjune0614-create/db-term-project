"""로그인 관련 공통 함수. 모든 기능에서 '현재 로그인한 사람'은 이걸로 꺼내 쓰기.

    from app.auth import current_user_id, login_required

    @router.get("/feed")
    def feed(request: Request):
        me = current_user_id(request)   # 로그인 안 했으면 None
        ...

로그인 성공 시:  request.session["user_id"] = user_id
로그아웃 시:     request.session.clear()
"""
import bcrypt
from fastapi import Request
from fastapi.responses import RedirectResponse


def current_user_id(request: Request):
    """로그인한 user_id, 없으면 None"""
    return request.session.get("user_id")


def login_required(request: Request):
    """로그인 안 했으면 로그인 페이지로 보내는 응답을, 했으면 None을 돌려줌

    redirect = login_required(request)
    if redirect:
        return redirect
    """
    if not current_user_id(request):
        return RedirectResponse("/login", status_code=303)
    return None


def hash_password(raw: str) -> str:
    return bcrypt.hashpw(raw.encode(), bcrypt.gensalt()).decode()


def check_password(raw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(raw.encode(), hashed.encode())
    except ValueError:
        # 샘플 데이터처럼 해시가 아닌 임시 비밀번호일 때
        return raw == hashed
