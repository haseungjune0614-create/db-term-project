"""프로필 및 팔로우 라우터: 프로필 조회, 팔로우/언팔로우, 팔로워/팔로잉 목록

- 연동 테이블: users, follows(복합 PK + 자기팔로우 방지 CHECK), posts
- 특징: 승인 절차 없이 즉시 팔로우/언팔로우 가능
"""
from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth import current_user_id, login_required
from app.db import execute, query_all, query_one

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def safe_next_url(next_url: str, fallback: str) -> str:
    """외부 사이트로의 악의적 리다이렉트(Open Redirect)를 막기 위해 내부 경로(/)만 허용"""
    if next_url and next_url.startswith("/") and not next_url.startswith("//"):
        return next_url
    return fallback


@router.get("/profile/{user_id}")
def profile_page(request: Request, user_id: str):
    """사용자 프로필 페이지: 기본 정보 + 통계(게시물/팔로워/팔로잉 수) + 3열 사진 그리드"""
    redirect = login_required(request)
    if redirect:
        return redirect

    me = current_user_id(request)
    # 스칼라 서브쿼리로 해당 유저의 게시물 수, 팔로워 수, 팔로잉 수를 한 번에 집계
    profile = query_one(
        """
        SELECT u.user_id, u.display_name,
               (SELECT COUNT(*) FROM posts   WHERE author_id   = %s) AS post_count,
               (SELECT COUNT(*) FROM follows WHERE followee_id = %s) AS follower_count,
               (SELECT COUNT(*) FROM follows WHERE follower_id = %s) AS following_count
        FROM users u
        WHERE u.user_id = %s
        """,
        (user_id, user_id, user_id, user_id),
    )
    if not profile:
        raise HTTPException(status_code=404, detail="존재하지 않는 사용자입니다.")

    # 해당 유저가 올린 게시물 목록 (최신순, idx_author_time 인덱스 활용)
    posts = query_all(
        "SELECT post_id, image_path FROM posts WHERE author_id = %s ORDER BY created_at DESC",
        (user_id,),
    )

    # 내가 이 사람을 팔로우 중인지 확인 (팔로우/팔로잉 버튼 토글 표시용)
    is_following = False
    if me != user_id:
        row = query_one(
            "SELECT COUNT(*) AS cnt FROM follows WHERE follower_id = %s AND followee_id = %s",
            (me, user_id),
        )
        is_following = row["cnt"] > 0

    return templates.TemplateResponse(
        request,
        "profile.html",
        {
            "me": me,
            "profile": profile,
            "posts": posts,
            "is_following": is_following,
        },
    )


@router.post("/profile/{user_id}/follow")
def follow_user(request: Request, user_id: str, next: str = Form("")):
    """즉시 팔로우 처리 (자기 자신 팔로우 및 복합 PK 중복 삽입 방지)"""
    redirect = login_required(request)
    if redirect:
        return redirect

    me = current_user_id(request)
    if me != user_id:
        row = query_one(
            "SELECT COUNT(*) AS cnt FROM follows WHERE follower_id = %s AND followee_id = %s",
            (me, user_id),
        )
        if row["cnt"] == 0:
            execute(
                "INSERT INTO follows (follower_id, followee_id) VALUES (%s, %s)",
                (me, user_id),
            )
    return RedirectResponse(safe_next_url(next, f"/profile/{user_id}"), status_code=303)


@router.post("/profile/{user_id}/unfollow")
def unfollow_user(request: Request, user_id: str, next: str = Form("")):
    """언팔로우 처리 (follows 테이블에서 해당 관계 행 삭제)"""
    redirect = login_required(request)
    if redirect:
        return redirect

    me = current_user_id(request)
    execute(
        "DELETE FROM follows WHERE follower_id = %s AND followee_id = %s",
        (me, user_id),
    )
    return RedirectResponse(safe_next_url(next, f"/profile/{user_id}"), status_code=303)


@router.get("/profile/{user_id}/followers")
def followers_page(request: Request, user_id: str):
    """특정 사용자를 팔로우하는 사람들(팔로워) 전체 목록"""
    redirect = login_required(request)
    if redirect:
        return redirect

    target = query_one(
        "SELECT user_id, display_name FROM users WHERE user_id = %s", (user_id,)
    )
    if not target:
        raise HTTPException(status_code=404, detail="존재하지 않는 사용자입니다.")

    # follows.followee_id = 대상 유저 -> follower_id를 users와 JOIN해 이름까지 조회
    users = query_all(
        """
        SELECT u.user_id, u.display_name
        FROM follows f
        JOIN users u ON f.follower_id = u.user_id
        WHERE f.followee_id = %s
        ORDER BY f.created_at DESC
        """,
        (user_id,),
    )
    return templates.TemplateResponse(
        request,
        "follow_list.html",
        {
            "me": current_user_id(request),
            "target": target,
            "title": "팔로워",
            "users": users,
        },
    )


@router.get("/profile/{user_id}/following")
def following_page(request: Request, user_id: str):
    """특정 사용자가 팔로우하고 있는 사람들(팔로잉) 전체 목록"""
    redirect = login_required(request)
    if redirect:
        return redirect

    target = query_one(
        "SELECT user_id, display_name FROM users WHERE user_id = %s", (user_id,)
    )
    if not target:
        raise HTTPException(status_code=404, detail="존재하지 않는 사용자입니다.")

    # follows.follower_id = 대상 유저 -> followee_id를 users와 JOIN해 이름까지 조회
    users = query_all(
        """
        SELECT u.user_id, u.display_name
        FROM follows f
        JOIN users u ON f.followee_id = u.user_id
        WHERE f.follower_id = %s
        ORDER BY f.created_at DESC
        """,
        (user_id,),
    )
    return templates.TemplateResponse(
        request,
        "follow_list.html",
        {
            "me": current_user_id(request),
            "target": target,
            "title": "팔로잉",
            "users": users,
        },
    )
