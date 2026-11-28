# DB 텀프로젝트(9조) 웹 애플리케이션 인수인계 가이드

> **대상 독자**: 최종 발표 담당(A), PPT 및 보고서 작성 담당(D)  
> **목적**: 웹 애플리케이션이 **무엇을 구현했고, 어떤 구조로, 어떻게 DB와 연동되어 작동하는지** 1시간 이내에 완전히 파악하여 발표·PPT·보고서 작성에 바로 활용할 수 있도록 정리한 문서입니다.

---

## 1. 한눈에 보는 구현 요약

**Instagram 스타일 사진 공유 웹 서비스**의 모든 필수 기능과 보너스 기능(좋아요, 1:1 메시지)을 구현했습니다.

| 구분 | 기능 | 연동 DB 테이블 | 구현 파일 |
| :--- | :--- | :--- | :--- |
| **필수** | 회원가입 / 로그인 / 로그아웃 / 비밀번호 변경 | `users` | `routers/auth_routes.py` |
| **필수** | 즉시 팔로우·언팔로우, 팔로워·팔로잉 목록 | `follows`, `users` | `routers/profile_routes.py` |
| **필수** | 프로필 조회 (통계 3종 + 3열 사진 그리드) | `users`, `posts`, `follows` | `routers/profile_routes.py` |
| **필수** | 사진 + 캡션 업로드, 홈 피드(최신순) | `posts`, `follows`, `users` | `routers/post_routes.py` |
| **필수** | 댓글 작성, `@아이디` 멘션 자동 프로필 링크 | `comments`, `users` | `routers/post_routes.py` |
| **보너스** | 좋아요 토글 및 개수 표시 | `likes` | `routers/post_routes.py` |
| **보너스** | 1:1 메시지(DM) 대화 목록·내역·전송 | `messages`, `users` | `routers/message_routes.py` |
| **UI/UX** | 인스타그램 스타일(호버 사이드바, 다크/화이트 모드) | - | `templates/base.html` 외 8개 |

### 과제 핵심 제약사항 준수 현황
1. **ORM 미사용 (Raw SQL 100%)**: SQLAlchemy 등 ORM 없이 `app/db.py`의 `PyMySQL` 커서로 SQL을 직접 실행합니다.
2. **SQL Injection 방지**: 모든 SQL 쿼리에 문자열 결합(`f-string`, `+`)을 쓰지 않고 **`%s` 파라미터 바인딩 + 튜플**만 사용합니다.
3. **서버 사이드 렌더링(SSR)**: React/Vue 없이 **FastAPI + Jinja2 HTML 템플릿**으로 화면을 렌더링합니다.
4. **이미지 분리 저장**: 실제 이미지 파일은 서버 로컬 폴더(`static/uploads/`)에 저장하고, DB `posts.image_path`에는 경로 문자열(`/uploads/파일명`)만 저장합니다.

---

## 2. 전체 동작 원리 (아키텍처)

사용자가 브라우저에서 버튼이나 링크를 클릭하면 아래 순서로 처리됩니다.

```text
[브라우저 (사용자)]
   │  ① HTTP 요청 (예: GET /feed, POST /posts/1/like)
   ▼
[main.py (FastAPI 서버 + SessionMiddleware)]
   │  ② 쿠키에서 로그인 세션(user_id) 확인 후 해당 라우터로 전달
   ▼
[routers/*.py (기능별 비즈니스 로직)]
   │  ③ 입력값 검증 + app/db.py 함수(query_one / query_all / execute) 호출
   ▼
[MySQL 8.0 (instagram DB — 6개 테이블)]
   │  ④ Raw SQL(%s 바인딩) 실행 후 결과(dict/list) 반환
   ▼
[templates/*.html (Jinja2 템플릿)]
   │  ⑤ DB 결과를 HTML에 채워 넣어 완성된 웹 페이지 생성
   ▼
[브라우저 화면 렌더링]
```

### 알아두면 좋은 핵심 메커니즘 3가지
* **로그인 유지 방식 (세션 쿠키)**: 로그인 성공 시 `request.session["user_id"] = user_id`로 암호화된 세션 쿠키에 아이디를 저장합니다. 이후 모든 페이지에서 `current_user_id(request)`로 현재 로그인 사용자를 확인하고, 비로그인 상태면 `/login`으로 자동 이동(`login_required`)시킵니다.
* **PRG 패턴 (Post → Redirect → Get)**: 글쓰기·팔로우·좋아요·댓글·DM 전송(`POST`) 후에는 항상 `303 Redirect`로 조회 페이지(`GET`)로 이동합니다. 덕분에 사용자가 새로고침(`F5`)을 눌러도 같은 요청이 중복 저장되지 않습니다.
* **정적 파일 서빙 (`/uploads`)**: `main.py`에서 `static/uploads/` 폴더를 `/uploads` URL 경로에 마운트했습니다. 따라서 DB에 저장된 `/uploads/alice1.jpg` 같은 경로가 그대로 `<img src="/uploads/alice1.jpg">`로 표시됩니다.

---

## 3. 폴더 및 파일 구조

```text
db-term-project/
├── main.py                    # 서버 시작점: FastAPI 생성, 세션/정적파일 설정, 4개 라우터 연결
├── app/                       # (역할 B 작성) 공통 유틸리티
│   ├── db.py                  # MySQL 연결 및 query_one / query_all / execute 공통 함수
│   └── auth.py                # 로그인 세션 확인(current_user_id, login_required) 및 bcrypt 해시
├── routers/                   # (역할 C 작성) 기능별 백엔드 라우터 + Raw SQL
│   ├── auth_routes.py         # 회원가입, 로그인, 로그아웃, 비밀번호 변경
│   ├── profile_routes.py      # 프로필 조회, 팔로우/언팔로우, 팔로워/팔로잉 목록
│   ├── post_routes.py         # 홈 피드, 사진 업로드, 게시물 상세, 댓글(@멘션), 좋아요
│   └── message_routes.py      # 1:1 메시지(DM) 대화 목록, 대화 내역, 메시지 전송
├── templates/                 # (역할 C 작성) Jinja2 HTML 화면
│   ├── base.html              # 공통 레이아웃(호버 확장 좌측 사이드바, 다크/화이트 모드 토글)
│   ├── login.html / signup.html / password.html   # 회원 관리 화면
│   ├── feed.html              # 홈 피드 (상단 팔로우 유저 바 + 게시물 + 우측 미팔로우 추천)
│   ├── upload.html            # 새 게시물(사진+캡션) 업로드 화면
│   ├── post_detail.html       # 게시물 상세 + 댓글 목록(@멘션 링크) + 댓글 작성
│   ├── profile.html           # 유저 프로필 (통계 + 팔로우/DM 버튼 + 3열 사진 그리드)
│   ├── follow_list.html       # 팔로워 / 팔로잉 목록 화면
│   └── messages.html          # 인스타그램 DM 스타일 2단 채팅 화면
├── static/uploads/            # 업로드된 실제 이미지 파일 저장소 (샘플 이미지 10장 포함)
└── sql/                       # (역할 B 작성) DB 스크립트
    ├── schema.sql             # 6개 테이블 생성 DDL (PK, FK, CHECK, INDEX)
    ├── sample_data.sql        # 테스트용 초기 데이터 (유저 5명, 게시물 10개 등)
    └── queries.sql            # 기능별 SQL 쿼리 모음
```

---

## 4. 기능별 동작 방식 & DB 연동 상세 (PPT/보고서용)

### 4.1 회원 관리 (`routers/auth_routes.py`)
* **회원가입 (`POST /signup`)**: 아이디 형식(영문/숫자/`_`, 30자 이내) 검사 → `SELECT COUNT(*)`로 중복 확인 → `bcrypt`로 비밀번호 해싱 후 `INSERT INTO users`.
* **로그인 (`POST /login`)**: `SELECT user_id, password, display_name FROM users WHERE user_id = %s`로 조회 → `check_password()`로 검증(해시 비밀번호와 샘플 데이터의 평문 임시 비밀번호 모두 지원) → 세션 저장 후 `/feed` 이동.
* **비밀번호 변경 (`POST /password`)**: 현재 비밀번호 일치 여부 확인 → 새 비밀번호를 `bcrypt` 해싱하여 `UPDATE users SET password = %s WHERE user_id = %s`.

### 4.2 팔로우 & 프로필 (`routers/profile_routes.py`)
* **프로필 조회 (`GET /profile/{user_id}`)**:
  * 스칼라 서브쿼리로 `게시물 수(posts)`, `팔로워 수(follows.followee_id)`, `팔로잉 수(follows.follower_id)`를 한 번에 조회합니다.
  * 해당 유저의 게시물을 최신순(`created_at DESC`)으로 가져와 3열 정사각형 그리드로 표시합니다.
* **팔로우 / 언팔로우 (`POST /profile/{user_id}/follow`, `/unfollow`)**:
  * 자기 자신 팔로우 방지(`me != user_id`, DB에도 `CHECK (follower_id <> followee_id)` 제약 존재) 및 중복 팔로우 체크 후 `INSERT` 또는 `DELETE`.
  * `next` 파라미터로 홈 피드 우측 추천에서 팔로우해도 피드에 그대로 머무르게 처리(오픈 리다이렉트 방지를 위해 내부 `/` 경로만 허용).
* **팔로워 / 팔로잉 목록 (`GET /profile/{user_id}/followers`, `/following`)**:
  * `follows`와 `users`를 `JOIN`하여 대상 유저의 팔로워/팔로잉 전체를 최신순으로 표시합니다.

### 4.3 홈 피드 & 사진 업로드 (`routers/post_routes.py`)
* **홈 피드 (`GET /feed`)**:
  * **게시물 스트림**: `WHERE p.author_id = %s OR p.author_id IN (SELECT followee_id FROM follows WHERE follower_id = %s)`로 **내 게시물 + 내가 팔로우한 사람 게시물**만 최신순 조회. 각 게시물의 좋아요 수, 댓글 수, 내가 좋아요 눌렀는지 여부까지 함께 가져옵니다.
  * **상단 스토리 위치 바**: 내가 **현재 팔로우한 사용자**만 표시(클릭 시 프로필 이동).
  * **우측 회원님을 위한 추천**: 내가 **아직 팔로우하지 않은 사용자** 최대 5명 표시(바로 팔로우 버튼 제공).
* **사진 업로드 (`POST /upload`)**:
  * 허용 확장자(`.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`) 검증 → 파일명 충돌 방지를 위해 `uuid4().hex + 확장자`로 `static/uploads/`에 저장 → DB `posts` 테이블에는 경로(`/uploads/파일명`)와 캡션만 `INSERT`.

### 4.4 댓글 & `@멘션` & 좋아요 (`routers/post_routes.py`)
* **댓글 작성 (`POST /posts/{post_id}/comments`)**: 공백 제거 후 `INSERT INTO comments`. (DB에도 `CHECK (CHAR_LENGTH(content) > 0)` 제약 존재)
* **`@아이디` 멘션 자동 링크 (`format_mentions`)**:
  1. 먼저 `markupsafe.escape()`로 사용자 입력을 HTML 이스케이프하여 **XSS 공격을 차단**합니다.
  2. 정규식 `@([A-Za-z0-9_]+)`로 멘션 패턴을 찾고, `SELECT COUNT(*) FROM users WHERE user_id = %s`로 **실제 가입된 유저인지 확인**합니다.
  3. 존재하는 유저일 때만 `<a href="/profile/{uid}" class="mention">@{uid}</a>` 링크로 변환하고, 없는 아이디는 일반 텍스트로 둡니다.
* **좋아요 토글 (`POST /posts/{post_id}/like`)**: `likes` 테이블은 `(user_id, post_id)` 복합 PK이므로, 이미 좋아요가 있으면 `DELETE`, 없으면 `INSERT`로 토글합니다.

### 4.5 1:1 메시지 / DM (`routers/message_routes.py`)
* **대화 상대 목록 (`GET /messages`)**: 내가 보낸 메시지(`sender_id = me`)와 받은 메시지(`receiver_id = me`)를 `UNION ALL`로 합친 뒤 `GROUP BY partner_id`와 `MAX(created_at)`으로 최근 대화 순 정렬합니다. 아직 대화한 적 없는 유저도 하단 `새 대화 시작` 목록에 노출해 바로 대화를 시작할 수 있습니다.
* **1:1 대화 내역 & 전송 (`GET/POST /messages/{partner_id}`)**: 두 사람 사이의 메시지를 `created_at ASC, message_id ASC` 순으로 불러와 말풍선 형태로 렌더링합니다. 자기 자신과의 DM은 코드와 DB(`CHECK (sender_id <> receiver_id)`) 양쪽에서 차단합니다.

### 4.6 전체 URL 라우트 요약표

| Method | URL | 기능 | 주요 SQL |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | 로그인 여부에 따라 `/feed` 또는 `/login` 이동 | - |
| `GET/POST` | `/signup` | 회원가입 | `SELECT COUNT(*)`, `INSERT INTO users` |
| `GET/POST` | `/login` | 로그인 | `SELECT ... FROM users` |
| `GET` | `/logout` | 로그아웃 (세션 초기화) | - |
| `GET/POST` | `/password` | 비밀번호 변경 | `UPDATE users SET password` |
| `GET` | `/feed` | 홈 피드 (팔로우+본인 게시물, 추천 유저) | `SELECT ... FROM posts JOIN users` |
| `GET/POST` | `/upload` | 사진 + 캡션 업로드 | `INSERT INTO posts` |
| `GET` | `/posts/{post_id}` | 게시물 상세 + 댓글(@멘션) | `SELECT ... FROM posts`, `comments` |
| `POST` | `/posts/{post_id}/comments` | 댓글 작성 | `INSERT INTO comments` |
| `POST` | `/posts/{post_id}/like` | 좋아요 토글 (보너스) | `INSERT` / `DELETE FROM likes` |
| `GET` | `/profile/{user_id}` | 프로필 통계 + 3열 사진 그리드 | `SELECT ... FROM users`, `posts`, `follows` |
| `POST` | `/profile/{user_id}/follow` | 팔로우 | `INSERT INTO follows` |
| `POST` | `/profile/{user_id}/unfollow` | 언팔로우 | `DELETE FROM follows` |
| `GET` | `/profile/{user_id}/followers` | 팔로워 목록 | `SELECT ... FROM follows JOIN users` |
| `GET` | `/profile/{user_id}/following` | 팔로잉 목록 | `SELECT ... FROM follows JOIN users` |
| `GET` | `/messages` | DM 대화 상대 목록 (보너스) | `UNION ALL` + `GROUP BY` on `messages` |
| `GET/POST` | `/messages/{partner_id}` | 1:1 채팅 내역 조회 및 전송 (보너스) | `SELECT` / `INSERT INTO messages` |

---

## 5. 발표 & 보고서에 어필할 기술 포인트

1. **DB 무결성 제약조건과 애플리케이션의 이중 보호**
   * `follows`·`likes`의 **복합 기본키(Composite PK)**로 중복 팔로우/중복 좋아요 원천 차단
   * `follows`, `messages`의 **`CHECK` 제약조건**으로 자기 자신 팔로우·자기 자신 DM 차단
   * `FOREIGN KEY ... ON DELETE CASCADE`로 유저/게시물 삭제 시 연관 데이터 자동 정리
   * `posts(author_id, created_at)` **복합 인덱스(`idx_author_time`)**로 프로필/피드 최신순 조회 성능 확보
2. **보안 고려**
   * **SQL Injection 방지**: 100% `%s` 파라미터 바인딩 사용
   * **비밀번호 보호**: `bcrypt` 단방향 해싱 + 솔트 적용
   * **XSS 방지**: 댓글 `@멘션` 변환 시 `escape()` 먼저 적용 후 검증된 유저 링크만 생성
   * **오픈 리다이렉트 방지**: `next` URL은 내부 경로(`/`로 시작, `//` 제외)만 허용
3. **실제 Instagram과 유사한 완성도 높은 UI**
   * 좌측 고정 사이드바(`position: fixed`): 평소엔 아이콘만 보이다가 마우스 호버 시 텍스트가 슬라이드로 확장(본문 밀림 없음)
   * 전 페이지 `display_name` 우선 표시 + `localStorage` 기반 **다크/화이트 모드 전환**

---

## 6. 라이브 데모 시연 가이드 (약 5분 코스)

### 서버 실행 방법
```powershell
.\venv\Scripts\activate
uvicorn main:app --reload
```
브라우저에서 `http://127.0.0.1:8000` 접속

### 기본 샘플 계정 (비밀번호 모두 `temp1234`)
* `alice` (Alice Kim) — 팔로잉: `bob`, `chris`, `dana` / DM 샘플 내역 보유
* `bob` (Bob Lee), `chris` (Chris Park), `dana` (Dana Choi), `eric` (Eric Jung)

### 추천 시연 순서
1. **회원가입 & 로그인**: `/signup`에서 새 계정(예: `demo_user` / `데모유저`) 가입 → `/login` 로그인 (또는 기존 `alice` / `temp1234`로 로그인)
2. **홈 피드 확인**:
   * 상단 바에는 **팔로우한 유저**만 표시됨을 설명
   * 우측 `회원님을 위한 추천`에는 **아직 팔로우하지 않은 유저**(`eric` 등)만 표시됨을 설명
3. **팔로우 & 팔로워/팔로잉 목록**: 우측 추천에서 `팔로우` 클릭 → 해당 유저가 상단 바로 이동하고 피드에 그 유저의 게시물이 나타남 → 프로필에서 팔로워/팔로잉 수 클릭해 목록 확인
4. **사진 업로드**: 왼쪽 사이드바 `게시물` 클릭 → 사진 선택 + 캡션 입력 후 공유 → 홈 피드 최상단에 즉시 반영 & `static/uploads/`에 저장됨 설명
5. **좋아요 & 댓글 `@멘션`**:
   * 하트 버튼 클릭(좋아요 토글 + 카운트 증가)
   * 댓글에 `@bob 사진 멋져요! @없는유저` 입력 → `@bob`은 클릭 가능한 프로필 링크로, `@없는유저`는 일반 텍스트로 렌더링됨을 강조!
6. **1:1 메시지(DM)**: 왼쪽 사이드바 `메시지` 클릭 → `bob`과 기존 대화 내역 확인 후 새 메시지 전송
7. **프로필 & 다크/화이트 모드 & 비밀번호 변경**:
   * 내 프로필 3열 그리드 확인
   * 좌측 하단 `화이트 모드 / 다크 모드` 토글 시연
   * `비밀번호 변경` 후 로그아웃 → 새 비밀번호로 재로그인 확인

---