-- =====================================================================
-- queries.sql : 웹 기능별 SQL 모음 (MySQL 8.0)
-- Python(PyMySQL / mysql-connector)에서 쓸 때는 %s 자리에 값을 넘겨주세요.
--   예) cursor.execute(sql, (user_id, password, display_name))
--   문자열을 직접 이어 붙이지 말 것 (SQL 인젝션 방지)
-- 직접 Workbench에서 테스트할 때는 %s 를 'alice' 같은 값으로 바꿔서 실행
-- =====================================================================


-- =========================== 1. 회원 관리 ===========================

-- [회원가입] (user_id, password(해시값), display_name)
INSERT INTO users (user_id, password, display_name)
VALUES (%s, %s, %s);

-- [아이디 중복 확인] 결과가 1이면 이미 있는 아이디
SELECT COUNT(*) FROM users WHERE user_id = %s;

-- [로그인] user_id로 저장된 비밀번호(해시)를 가져와서 Python에서 비교
SELECT user_id, password, display_name
FROM users
WHERE user_id = %s;

-- [비밀번호 변경] (새 비밀번호 해시, user_id)
UPDATE users
SET password = %s
WHERE user_id = %s;


-- =========================== 2. 팔로우 ===========================

-- [팔로우] (나, 상대)  ※ 승인 없이 바로 팔로우
INSERT INTO follows (follower_id, followee_id)
VALUES (%s, %s);

-- [언팔로우] (나, 상대)
DELETE FROM follows
WHERE follower_id = %s AND followee_id = %s;

-- [팔로우 중인지 확인] (나, 상대) → 1이면 팔로우 중 (프로필의 팔로우/언팔로우 버튼용)
SELECT COUNT(*) FROM follows
WHERE follower_id = %s AND followee_id = %s;

-- [팔로워 목록] 이 사람(user_id)을 팔로우하는 사람들
SELECT u.user_id, u.display_name
FROM follows f
JOIN users u ON f.follower_id = u.user_id
WHERE f.followee_id = %s
ORDER BY f.created_at DESC;

-- [팔로잉 목록] 이 사람(user_id)이 팔로우하는 사람들
SELECT u.user_id, u.display_name
FROM follows f
JOIN users u ON f.followee_id = u.user_id
WHERE f.follower_id = %s
ORDER BY f.created_at DESC;


-- =========================== 3. 게시물 ===========================

-- [게시물 업로드] (작성자, 사진 경로, 캡션)
--   사진 파일은 uploads/ 폴더에 저장하고 경로만 DB에 넣기
INSERT INTO posts (author_id, image_path, caption)
VALUES (%s, %s, %s);

-- [홈 피드] 내 게시물 + 내가 팔로우한 사람 게시물, 최신순
--   (로그인한 user_id, 로그인한 user_id) 두 번 넘기기
SELECT p.post_id, p.author_id, u.display_name, p.image_path, p.caption, p.created_at,
       (SELECT COUNT(*) FROM likes l    WHERE l.post_id = p.post_id) AS like_count,
       (SELECT COUNT(*) FROM comments c WHERE c.post_id = p.post_id) AS comment_count
FROM posts p
JOIN users u ON p.author_id = u.user_id
WHERE p.author_id = %s
   OR p.author_id IN (SELECT followee_id FROM follows WHERE follower_id = %s)
ORDER BY p.created_at DESC;

-- [게시물 하나 보기] (post_id)
SELECT p.post_id, p.author_id, u.display_name, p.image_path, p.caption, p.created_at
FROM posts p
JOIN users u ON p.author_id = u.user_id
WHERE p.post_id = %s;


-- =========================== 4. 프로필 ===========================

-- [프로필 기본 정보 + 게시물/팔로워/팔로잉 수] (같은 user_id를 4번 넘기기)
SELECT u.user_id, u.display_name,
       (SELECT COUNT(*) FROM posts   WHERE author_id   = %s) AS post_count,
       (SELECT COUNT(*) FROM follows WHERE followee_id = %s) AS follower_count,
       (SELECT COUNT(*) FROM follows WHERE follower_id = %s) AS following_count
FROM users u
WHERE u.user_id = %s;

-- [프로필 사진 그리드] 이 사람이 올린 게시물, 최신순 (user_id)
SELECT post_id, image_path
FROM posts
WHERE author_id = %s
ORDER BY created_at DESC;


-- =========================== 5. 댓글 ===========================

-- [댓글 작성] (post_id, 작성자, 내용)  ※ @멘션은 content 안에 그대로 저장
INSERT INTO comments (post_id, author_id, content)
VALUES (%s, %s, %s);

-- [댓글 목록] 게시물(post_id)의 댓글, 오래된 순
SELECT c.comment_id, c.author_id, u.display_name, c.content, c.created_at
FROM comments c
JOIN users u ON c.author_id = u.user_id
WHERE c.post_id = %s
ORDER BY c.created_at ASC;

-- [멘션 대상이 실제 유저인지 확인] (@뒤의 아이디) → 1이면 링크로 표시
SELECT COUNT(*) FROM users WHERE user_id = %s;


-- =========================== 6. 좋아요 (보너스) ===========================

-- [좋아요] (user_id, post_id)  ※ 복합 PK라 두 번 누르면 에러 → 그 전에 아래 확인 쿼리로 체크
INSERT INTO likes (user_id, post_id)
VALUES (%s, %s);

-- [좋아요 취소] (user_id, post_id)
DELETE FROM likes
WHERE user_id = %s AND post_id = %s;

-- [내가 좋아요 눌렀는지] (user_id, post_id) → 1이면 ❤️, 0이면 ♡
SELECT COUNT(*) FROM likes
WHERE user_id = %s AND post_id = %s;


-- =========================== 7. 메시지 (보너스) ===========================

-- [메시지 보내기] (보내는 사람, 받는 사람, 내용)
INSERT INTO messages (sender_id, receiver_id, content)
VALUES (%s, %s, %s);

-- [두 사람 대화 내역] (나, 상대, 상대, 나) 순서로 4번 넘기기
SELECT m.message_id, m.sender_id, m.content, m.created_at
FROM messages m
WHERE (m.sender_id = %s AND m.receiver_id = %s)
   OR (m.sender_id = %s AND m.receiver_id = %s)
ORDER BY m.created_at ASC;

-- [대화 상대 목록] 나(user_id)와 메시지를 주고받은 사람들, 최근 대화 순
--   (나, 나, 나) 3번 넘기기
SELECT partner_id, MAX(created_at) AS last_time
FROM (
    SELECT receiver_id AS partner_id, created_at FROM messages WHERE sender_id   = %s
    UNION ALL
    SELECT sender_id   AS partner_id, created_at FROM messages WHERE receiver_id = %s
) t
GROUP BY partner_id
ORDER BY last_time DESC;
