"""메시지(DM) 라우터(보너스 기능): 대화 상대 목록, 1:1 대화 내역, 메시지 전송

- 연동 테이블: messages (message_id PK, sender_id, receiver_id, content, created_at), users
- 제약조건 대응: DB의 CHECK (sender_id <> receiver_id)에 맞춰 자기 자신과의 DM은 자동 차단
"""
from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth import current_user_id, login_required
from app.db import execute, query_all, query_one
from routers.post_routes import format_time_ago

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def _load_dm_sidebar(me: str):
    """좌측 DM 목록 조회:
    1) 나와 메시지를 주고받은 상대 목록 (UNION ALL + GROUP BY로 최근 대화 순 정렬)
    2) 아직 대화한 적 없는 나머지 유저 목록 (새 대화 시작용)
    """
    partners = query_all(
        """
        SELECT t.partner_id, u.display_name, MAX(t.created_at) AS last_time
        FROM (
            SELECT receiver_id AS partner_id, created_at FROM messages WHERE sender_id = %s
            UNION ALL
            SELECT sender_id   AS partner_id, created_at FROM messages WHERE receiver_id = %s
        ) t
        JOIN users u ON u.user_id = t.partner_id
        GROUP BY t.partner_id, u.display_name
        ORDER BY last_time DESC
        """,
        (me, me),
    )

    for p in partners:
        last_msg = query_one(
            """
            SELECT sender_id, content, created_at
            FROM messages
            WHERE (sender_id = %s AND receiver_id = %s)
               OR (sender_id = %s AND receiver_id = %s)
            ORDER BY created_at DESC, message_id DESC
            LIMIT 1
            """,
            (me, p["partner_id"], p["partner_id"], me),
        )
        p["last_content"] = last_msg["content"] if last_msg else ""
        p["last_sender"] = last_msg["sender_id"] if last_msg else ""
        p["time_ago"] = format_time_ago(p["last_time"])

    partner_ids = {p["partner_id"] for p in partners}
    all_others = query_all(
        """
        SELECT user_id, display_name
        FROM users
        WHERE user_id <> %s
        ORDER BY user_id ASC
        """,
        (me,),
    )
    new_users = [u for u in all_others if u["user_id"] not in partner_ids]
    return partners, new_users


@router.get("/messages")
def messages_inbox(request: Request):
    """DM 기본 화면 (대화 상대 미선택 상태)"""
    redirect = login_required(request)
    if redirect:
        return redirect

    me = current_user_id(request)
    my_user = query_one(
        "SELECT user_id, display_name FROM users WHERE user_id = %s",
        (me,),
    )
    partners, new_users = _load_dm_sidebar(me)

    return templates.TemplateResponse(
        request,
        "messages.html",
        {
            "me": me,
            "my_user": my_user,
            "partners": partners,
            "new_users": new_users,
            "partner": None,
            "chat_messages": [],
        },
    )


@router.get("/messages/{partner_id}")
def messages_chat(request: Request, partner_id: str):
    """특정 상대와의 1:1 채팅방: 두 사람 간 메시지를 시간 오름차순(ASC)으로 조회"""
    redirect = login_required(request)
    if redirect:
        return redirect

    me = current_user_id(request)
    if partner_id == me:
        return RedirectResponse("/messages", status_code=303)

    partner = query_one(
        "SELECT user_id, display_name FROM users WHERE user_id = %s",
        (partner_id,),
    )
    if not partner:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    my_user = query_one(
        "SELECT user_id, display_name FROM users WHERE user_id = %s",
        (me,),
    )
    partners, new_users = _load_dm_sidebar(me)
    chat_messages = query_all(
        """
        SELECT m.message_id, m.sender_id, m.content, m.created_at
        FROM messages m
        WHERE (m.sender_id = %s AND m.receiver_id = %s)
           OR (m.sender_id = %s AND m.receiver_id = %s)
        ORDER BY m.created_at ASC, m.message_id ASC
        """,
        (me, partner_id, partner_id, me),
    )

    for m in chat_messages:
        m["time_label"] = m["created_at"].strftime("%m/%d %H:%M") if m["created_at"] else ""

    return templates.TemplateResponse(
        request,
        "messages.html",
        {
            "me": me,
            "my_user": my_user,
            "partners": partners,
            "new_users": new_users,
            "partner": partner,
            "chat_messages": chat_messages,
        },
    )


@router.post("/messages/{partner_id}")
def send_message(
    request: Request,
    partner_id: str,
    content: str = Form(""),
):
    """1:1 메시지 전송: messages 테이블에 INSERT 후 해당 채팅방으로 리다이렉트"""
    redirect = login_required(request)
    if redirect:
        return redirect

    me = current_user_id(request)
    if partner_id == me:
        return RedirectResponse("/messages", status_code=303)

    partner = query_one("SELECT user_id FROM users WHERE user_id = %s", (partner_id,))
    if not partner:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    text = content.strip()
    if text:
        execute(
            "INSERT INTO messages (sender_id, receiver_id, content) VALUES (%s, %s, %s)",
            (me, partner_id, text[:1000]),
        )

    return RedirectResponse(f"/messages/{partner_id}", status_code=303)
