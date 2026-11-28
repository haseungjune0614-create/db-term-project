"""게시물 라우터: 홈 피드, 사진 업로드, 게시물 상세, 댓글(@멘션), 좋아요

- 연동 테이블: posts, comments, likes, follows, users
- 이미지 처리: 실제 파일은 static/uploads/에 UUID 이름으로 저장, DB에는 경로(/uploads/...)만 저장
- 멘션 처리: 댓글 내 @아이디가 실제 가입된 유저면 프로필 링크로 변환 (XSS 방지를 위해 먼저 escape 적용)
"""
from datetime import datetime
import os
import re
import uuid

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from markupsafe import Markup, escape

from app.auth import current_user_id, login_required
from app.db import execute, query_all, query_one

router = APIRouter()
templates = Jinja2Templates(directory="templates")

UPLOAD_DIR = os.path.join("static", "uploads")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


def safe_next_url(next_url: str, fallback: str) -> str:
    """오픈 리다이렉트 방지를 위해 내부 경로(/)만 허용"""
    if next_url and next_url.startswith("/") and not next_url.startswith("//"):
        return next_url
    return fallback


def format_time_ago(dt) -> str:
    """인스타그램 스타일 상대 시간 표시 (예: 방금, 15분, 8시간, 3일)"""
    if not isinstance(dt, datetime):
        return str(dt or "")
    diff = datetime.now() - dt
    seconds = int(diff.total_seconds())
    if seconds < 60:
        return "방금"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}분"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}시간"
    days = hours // 24
    if days < 7:
        return f"{days}일"
    weeks = days // 7
    if weeks < 5:
        return f"{weeks}주"
    return dt.strftime("%Y.%m.%d")


def format_mentions(text: str) -> Markup:
    """댓글 내 @아이디가 실제 가입된 유저면 프로필 링크로 변환"""
    if not text:
        return Markup("")

    # 1) HTML 특수문자를 먼저 이스케이프하여 XSS(스크립트 삽입) 공격 방지
    escaped = str(escape(text))

    # 2) @영문/숫자/밑줄 패턴을 찾아 DB users 테이블에 실제로 존재하는 아이디만 <a> 태그로 변환
    def replace_mention(match):
        uid = match.group(1)
        row = query_one("SELECT COUNT(*) AS cnt FROM users WHERE user_id = %s", (uid,))
        if row and row["cnt"] > 0:
            return f'<a href="/profile/{uid}" class="mention">@{uid}</a>'
        return f"@{uid}"

    return Markup(re.sub(r"@([A-Za-z0-9_]+)", replace_mention, escaped))


@router.get("/feed")
def feed_page(request: Request):
    """홈 피드: 내 게시물 + 팔로우한 유저 게시물(최신순), 상단 팔로우 유저 바, 우측 미팔로우 추천"""
    redirect = login_required(request)
    if redirect:
        return redirect

    me = current_user_id(request)
    my_user = query_one(
        "SELECT user_id, display_name FROM users WHERE user_id = %s",
        (me,),
    )

    # 피드 게시물 조회: 본인 게시물 OR 내가 팔로우한 사람들의 게시물 + 좋아요/댓글 통계
    posts = query_all(
        """
        SELECT p.post_id, p.author_id, u.display_name, p.image_path, p.caption, p.created_at,
               (SELECT COUNT(*) FROM likes l    WHERE l.post_id = p.post_id) AS like_count,
               (SELECT COUNT(*) FROM comments c WHERE c.post_id = p.post_id) AS comment_count,
               (SELECT COUNT(*) FROM likes l    WHERE l.post_id = p.post_id AND l.user_id = %s) AS liked_by_me
        FROM posts p
        JOIN users u ON p.author_id = u.user_id
        WHERE p.author_id = %s
           OR p.author_id IN (SELECT followee_id FROM follows WHERE follower_id = %s)
        ORDER BY p.created_at DESC
        """,
        (me, me, me),
    )
    for post in posts:
        post["time_ago"] = format_time_ago(post["created_at"])

    # 상단 스토리 바: 내가 현재 팔로우한 사용자만 표시
    story_users = query_all(
        """
        SELECT u.user_id, u.display_name
        FROM follows f
        JOIN users u ON f.followee_id = u.user_id
        WHERE f.follower_id = %s
        ORDER BY f.created_at DESC
        """,
        (me,),
    )

    # 우측 회원님을 위한 추천: 아직 팔로우하지 않은 사용자 최대 5명
    suggested_users = query_all(
        """
        SELECT user_id, display_name
        FROM users
        WHERE user_id <> %s
          AND user_id NOT IN (SELECT followee_id FROM follows WHERE follower_id = %s)
        ORDER BY created_at DESC
        LIMIT 5
        """,
        (me, me),
    )

    return templates.TemplateResponse(
        request,
        "feed.html",
        {
            "me": me,
            "my_user": my_user,
            "posts": posts,
            "story_users": story_users,
            "suggested_users": suggested_users,
        },
    )


@router.get("/upload")
def upload_page(request: Request):
    redirect = login_required(request)
    if redirect:
        return redirect

    return templates.TemplateResponse(
        request,
        "upload.html",
        {"me": current_user_id(request), "error": None},
    )


@router.post("/upload")
async def upload_submit(
    request: Request,
    image: UploadFile = File(...),
    caption: str = Form(""),
):
    """사진 + 캡션 업로드: 파일 확장자 검사 -> UUID 파일명으로 로컬 저장 -> DB에 경로만 INSERT"""
    redirect = login_required(request)
    if redirect:
        return redirect

    me = current_user_id(request)
    ext = os.path.splitext(image.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return templates.TemplateResponse(
            request,
            "upload.html",
            {"me": me, "error": "이미지 파일(jpg, jpeg, png, gif, webp)만 업로드할 수 있습니다."},
        )

    # 파일명 충돌을 막기 위해 랜덤 UUID로 파일명 생성 후 static/uploads/에 저장
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{ext}"
    save_path = os.path.join(UPLOAD_DIR, filename)

    data = await image.read()
    with open(save_path, "wb") as f:
        f.write(data)

    # 캡션이 비어 있으면 DB에 NULL 저장 (posts.caption은 nullable)
    caption_value = caption.strip() if caption.strip() else None
    execute(
        "INSERT INTO posts (author_id, image_path, caption) VALUES (%s, %s, %s)",
        (me, f"/uploads/{filename}", caption_value),
    )
    return RedirectResponse("/feed", status_code=303)


@router.get("/posts/{post_id}")
def post_detail_page(request: Request, post_id: int):
    """게시물 상세 페이지: 사진, 캡션, 좋아요 수, 오래된 순 댓글 목록(@멘션 링크 포함)"""
    redirect = login_required(request)
    if redirect:
        return redirect

    me = current_user_id(request)
    post = query_one(
        """
        SELECT p.post_id, p.author_id, u.display_name, p.image_path, p.caption, p.created_at,
               (SELECT COUNT(*) FROM likes l    WHERE l.post_id = p.post_id) AS like_count,
               (SELECT COUNT(*) FROM comments c WHERE c.post_id = p.post_id) AS comment_count,
               (SELECT COUNT(*) FROM likes l    WHERE l.post_id = p.post_id AND l.user_id = %s) AS liked_by_me
        FROM posts p
        JOIN users u ON p.author_id = u.user_id
        WHERE p.post_id = %s
        """,
        (me, post_id),
    )
    if not post:
        raise HTTPException(status_code=404, detail="게시물을 찾을 수 없습니다.")

    post["time_ago"] = format_time_ago(post["created_at"])

    comments = query_all(
        """
        SELECT c.comment_id, c.author_id, u.display_name, c.content, c.created_at
        FROM comments c
        JOIN users u ON c.author_id = u.user_id
        WHERE c.post_id = %s
        ORDER BY c.created_at ASC
        """,
        (post_id,),
    )
    for c in comments:
        c["formatted_content"] = format_mentions(c["content"])
        c["time_ago"] = format_time_ago(c["created_at"])

    return templates.TemplateResponse(
        request,
        "post_detail.html",
        {"me": me, "post": post, "comments": comments},
    )


@router.post("/posts/{post_id}/comments")
def add_comment(
    request: Request,
    post_id: int,
    content: str = Form(""),
    next: str = Form(""),
):
    """댓글 작성 처리 (빈 문자열은 DB CHECK 제약 위반이므로 공백 제거 후 값이 있을 때만 INSERT)"""
    redirect = login_required(request)
    if redirect:
        return redirect

    me = current_user_id(request)
    text = content.strip()
    if text:
        execute(
            "INSERT INTO comments (post_id, author_id, content) VALUES (%s, %s, %s)",
            (post_id, me, text),
        )
    return RedirectResponse(safe_next_url(next, f"/posts/{post_id}"), status_code=303)


@router.post("/posts/{post_id}/like")
def toggle_like(
    request: Request,
    post_id: int,
    next: str = Form(""),
):
    """좋아요 토글(보너스 기능): likes 복합 PK(user_id, post_id) 존재 여부에 따라 DELETE 또는 INSERT"""
    redirect = login_required(request)
    if redirect:
        return redirect

    me = current_user_id(request)
    row = query_one(
        "SELECT COUNT(*) AS cnt FROM likes WHERE user_id = %s AND post_id = %s",
        (me, post_id),
    )
    if row["cnt"] > 0:
        execute(
            "DELETE FROM likes WHERE user_id = %s AND post_id = %s",
            (me, post_id),
        )
    else:
        execute(
            "INSERT INTO likes (user_id, post_id) VALUES (%s, %s)",
            (me, post_id),
        )
    return RedirectResponse(safe_next_url(next, f"/posts/{post_id}"), status_code=303)
