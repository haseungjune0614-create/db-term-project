-- schema.sql : 테이블 생성 (MySQL 8.0.16 이상, CHECK 제약 사용)
CREATE DATABASE IF NOT EXISTS instagram;
USE instagram;

CREATE TABLE users (
  user_id      VARCHAR(30)  PRIMARY KEY,
  password     VARCHAR(255) NOT NULL,
  display_name VARCHAR(50)  NOT NULL,
  created_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE follows (
  follower_id VARCHAR(30) NOT NULL,
  followee_id VARCHAR(30) NOT NULL,
  created_at  DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (follower_id, followee_id),
  FOREIGN KEY (follower_id) REFERENCES users(user_id) ON DELETE CASCADE,
  FOREIGN KEY (followee_id) REFERENCES users(user_id) ON DELETE CASCADE,
  CHECK (follower_id <> followee_id)
);

CREATE TABLE posts (
  post_id    INT AUTO_INCREMENT PRIMARY KEY,
  author_id  VARCHAR(30)   NOT NULL,
  image_path VARCHAR(255)  NOT NULL,
  caption    VARCHAR(2200),
  created_at DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (author_id) REFERENCES users(user_id) ON DELETE CASCADE,
  INDEX idx_author_time (author_id, created_at)
);

CREATE TABLE comments (
  comment_id INT AUTO_INCREMENT PRIMARY KEY,
  post_id    INT           NOT NULL,
  author_id  VARCHAR(30)   NOT NULL,
  content    VARCHAR(1000) NOT NULL,
  created_at DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (post_id)   REFERENCES posts(post_id)  ON DELETE CASCADE,
  FOREIGN KEY (author_id) REFERENCES users(user_id) ON DELETE CASCADE,
  CHECK (CHAR_LENGTH(content) > 0)
);

CREATE TABLE likes (
  user_id    VARCHAR(30) NOT NULL,
  post_id    INT         NOT NULL,
  created_at DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (user_id, post_id),
  FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
  FOREIGN KEY (post_id) REFERENCES posts(post_id) ON DELETE CASCADE
);

CREATE TABLE messages (
  message_id  INT AUTO_INCREMENT PRIMARY KEY,
  sender_id   VARCHAR(30)   NOT NULL,
  receiver_id VARCHAR(30)   NOT NULL,
  content     VARCHAR(1000) NOT NULL,
  created_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (sender_id)   REFERENCES users(user_id) ON DELETE CASCADE,
  FOREIGN KEY (receiver_id) REFERENCES users(user_id) ON DELETE CASCADE,
  CHECK (sender_id <> receiver_id)
);
