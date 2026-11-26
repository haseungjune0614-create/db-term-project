# DB 텀프로젝트: Instagram 스타일 사진 공유 서비스

FastAPI + Jinja2 + MySQL 8.0

## 처음 세팅 (각자 한 번만)

### 1. 코드 받기
```bash
git clone <레포 주소>
cd <레포 폴더>
```

### 2. MySQL에 DB 만들기
MySQL Workbench에서 아래 두 파일을 순서대로 열고 **번개 아이콘 ⚡(전체 실행)** 클릭
1. `sql/schema.sql`: 테이블 생성
2. `sql/sample_data.sql`: 테스트 데이터

왼쪽 Schemas 새로고침해서 `instagram` DB에 테이블 6개 있으면 OK

### 3. 파이썬 패키지 설치
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Mac
source venv/bin/activate

pip install -r requirements.txt
```

### 4. 비밀번호 파일 만들기
`.env.example`을 복사해서 이름을 `.env`로 바꾸고, `DB_PASSWORD`에 **자기 MySQL root 비밀번호** 입력
(`.env`는 GitHub에 안 올라가요. 각자 비밀번호가 달라도 됨)

### 5. 실행
```bash
uvicorn main:app --reload
```
브라우저에서 http://127.0.0.1:8000 → **"세팅 성공 🎉"** 화면이 나오면 끝

## 폴더 구조
```
main.py              서버 시작점 (기능 라우터 붙이는 곳)
app/db.py            DB 연결 공통 함수 (query_one / query_all / execute)
app/auth.py          로그인 공통 함수 (current_user_id, 비밀번호 해시)
routers/             각자 기능 파일 (예: auth_routes.py, post_routes.py)
templates/           HTML (base.html 상속해서 만들기)
static/uploads/      업로드된 사진 저장 위치
sql/schema.sql       테이블 생성 (최종 DDL)
sql/sample_data.sql  테스트 데이터
sql/queries.sql      기능별 SQL 모음 (여기서 복사해서 쓰기)
```

## 협업 규칙
- **작업 전에 항상** `git pull`
- 기능별 브랜치에서 작업 후 Pull Request (예: `feature/login`, `feature/feed`)
- **자기 담당 파일만** 수정하기. `main.py`, `app/db.py`, `base.html` 수정이 필요하면 단톡에 먼저 말하기
- 로그인한 사람 ID는 `current_user_id(request)` 로만 꺼내 쓰기
- SQL은 `sql/queries.sql`에서 복사. 값은 반드시 `%s` + 튜플로 넘기기 (문자열 이어 붙이기 금지)
- DB 구조(테이블/컬럼) 바꾸려면 `sql/schema.sql` 수정하고 단톡 공지 → 다들 schema.sql 다시 실행

## DB를 처음 상태로 되돌리고 싶을 때
Workbench에서 `DROP DATABASE instagram;` 실행 후 2번 다시 하기
