CREATE TABLE IF NOT EXISTS qb_question (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 owner_id INT NOT NULL,
 subject VARCHAR(40) NOT NULL,
 grade VARCHAR(40) NOT NULL,
 question_type VARCHAR(20) NOT NULL,
 difficulty VARCHAR(20) NOT NULL,
 stem TEXT NOT NULL,
 knowledge_points VARCHAR(500) NOT NULL DEFAULT '',
 content_json MEDIUMTEXT NOT NULL,
 status VARCHAR(20) NOT NULL DEFAULT 'draft',
 review_note VARCHAR(1000) NOT NULL DEFAULT '',
 reviewer_id INT NULL,
 revision INT NOT NULL DEFAULT 1,
 created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 KEY idx_qb_public(status,subject,grade,question_type,difficulty,id),
 KEY idx_qb_owner(owner_id,status,id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE IF NOT EXISTS qb_paper (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 owner_id INT NOT NULL,
 title VARCHAR(120) NOT NULL,
 subject VARCHAR(40) NOT NULL,
 duration_minutes INT NOT NULL,
 total_score DECIMAL(8,2) NOT NULL,
 content_json MEDIUMTEXT NOT NULL,
 revision INT NOT NULL DEFAULT 1,
 created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 KEY idx_qb_paper_owner(owner_id,id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE IF NOT EXISTS qb_review (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 question_id BIGINT NOT NULL,
 reviewer_id INT NOT NULL,
 decision VARCHAR(20) NOT NULL,
 note VARCHAR(1000) NOT NULL DEFAULT '',
 question_revision INT NOT NULL,
 created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 KEY idx_qb_review_question(question_id,id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
