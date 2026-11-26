-- sample_data.sql : 테스트/데모용 데이터 (schema.sql 실행 후)
USE instagram;

-- 비밀번호는 임시값. 로그인 기능에서 해시를 쓰면 그 방식으로 만든 값으로 교체
INSERT INTO users (user_id, password, display_name) VALUES
('alice',  'temp1234', 'Alice Kim'),
('bob',    'temp1234', 'Bob Lee'),
('chris',  'temp1234', 'Chris Park'),
('dana',   'temp1234', 'Dana Choi'),
('eric',   'temp1234', 'Eric Jung');

INSERT INTO follows (follower_id, followee_id) VALUES
('alice', 'bob'), ('alice', 'chris'), ('alice', 'dana'),
('bob', 'alice'), ('bob', 'chris'),
('chris', 'alice'), ('chris', 'eric'),
('dana', 'alice'), ('dana', 'bob'),
('eric', 'alice');

INSERT INTO posts (author_id, image_path, caption, created_at) VALUES
('alice', '/uploads/alice1.jpg', '첫 게시물!',     '2026-11-20 10:00:00'),
('bob',   '/uploads/bob1.jpg',   '오늘 점심 #맛집', '2026-11-21 12:30:00'),
('chris', '/uploads/chris1.jpg', '한강 산책',       '2026-11-22 18:00:00'),
('dana',  '/uploads/dana1.jpg',  '새 카메라 샀다',   '2026-11-23 09:15:00'),
('eric',  '/uploads/eric1.jpg',  '야구 직관 ⚾',    '2026-11-23 20:00:00'),
('alice', '/uploads/alice2.jpg', '주말 카페',       '2026-11-24 15:00:00'),
('bob',   '/uploads/bob2.jpg',   NULL,              '2026-11-25 11:00:00'),
('chris', '/uploads/chris2.jpg', '시험 공부 중...', '2026-11-25 22:00:00'),
('dana',  '/uploads/dana2.jpg',  '노을 사진',       '2026-11-26 17:30:00'),
('eric',  '/uploads/eric2.jpg',  '운동 끝',         '2026-11-26 19:00:00');

INSERT INTO comments (post_id, author_id, content) VALUES
(1, 'bob',   '환영해요!'),
(2, 'alice', '@chris 여기 같이 가자'),
(3, 'alice', '사진 예쁘다'),
(6, 'dana',  '@alice 어디 카페야?'),
(6, 'alice', '@dana 학교 앞!'),
(9, 'bob',   '와 대박');

INSERT INTO likes (user_id, post_id) VALUES
('bob', 1), ('chris', 1), ('dana', 1),
('alice', 2), ('alice', 3), ('bob', 6), ('dana', 6), ('alice', 9);

INSERT INTO messages (sender_id, receiver_id, content) VALUES
('alice', 'bob',   '내일 과제 회의 몇 시?'),
('bob',   'alice', '3시 어때?'),
('dana',  'alice', '카페 이름 알려줘');
