"""MySQL 연결 공통 코드. 모든 기능에서 이 파일의 함수만 쓰세요.

사용 예:
    from app.db import query_one, query_all, execute

    user = query_one("SELECT * FROM users WHERE user_id = %s", (user_id,))
    posts = query_all("SELECT * FROM posts WHERE author_id = %s", (user_id,))
    execute("INSERT INTO follows (follower_id, followee_id) VALUES (%s, %s)", (me, target))

※ SQL에 값을 문자열로 이어 붙이지 말고 반드시 %s + 튜플로 넘기기 (SQL 인젝션 방지)
※ 값이 하나여도 (user_id,) 처럼 쉼표를 붙여야 튜플이 됨
"""
import os

import pymysql
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    return pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "instagram"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,  # 결과를 dict로 받기: row["user_id"]
    )


def query_one(sql, params=()):
    """결과 한 줄(dict) 또는 None"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone()
    finally:
        conn.close()


def query_all(sql, params=()):
    """결과 여러 줄(list of dict)"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()
    finally:
        conn.close()


def execute(sql, params=()):
    """INSERT / UPDATE / DELETE. 새로 생긴 AUTO_INCREMENT id를 돌려줌"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
        conn.commit()
        return cur.lastrowid
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
