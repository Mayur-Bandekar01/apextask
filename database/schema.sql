-- ==========================================================
-- ULTIMATE TO-DO LIST WEB APP — CLOUD MYSQL DATABASE SCHEMA
-- Target DBs: PlanetScale, Railway, Aiven, AWS RDS, Local MySQL
-- ==========================================================

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    title VARCHAR(100) DEFAULT 'Productivity Architect',
    xp INT DEFAULT 0,
    level INT DEFAULT 1,
    streak INT DEFAULT 0,
    last_active DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tasks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    title VARCHAR(255) NOT NULL,
    notes TEXT,
    priority ENUM('low', 'medium', 'high') DEFAULT 'medium',
    status ENUM('pending', 'complete', 'missed') DEFAULT 'pending',
    original_date DATE NOT NULL,
    deadline DATETIME,
    rollover_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_date_status (user_id, original_date, status),
    INDEX idx_user_deadline (user_id, deadline)
);

CREATE TABLE IF NOT EXISTS task_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    task_id INT NOT NULL,
    change_description VARCHAR(255) NOT NULL,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    INDEX idx_task_log (task_id, changed_at)
);

CREATE TABLE IF NOT EXISTS badges (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    badge_name VARCHAR(100) NOT NULL,
    earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY uq_user_badge (user_id, badge_name)
);

CREATE TABLE IF NOT EXISTS daily_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    record_date DATE NOT NULL,
    tasks_completed INT DEFAULT 0,
    tasks_missed INT DEFAULT 0,
    xp_earned INT DEFAULT 0,
    focus_time INT DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY uq_user_record_date (user_id, record_date),
    INDEX idx_user_record_date (user_id, record_date)
);

CREATE TABLE IF NOT EXISTS challenges (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    challenge_type ENUM('daily', 'weekly') NOT NULL DEFAULT 'daily',
    title VARCHAR(255) NOT NULL,
    description TEXT,
    target_count INT NOT NULL DEFAULT 3,
    current_count INT NOT NULL DEFAULT 0,
    xp_reward INT NOT NULL DEFAULT 100,
    is_completed TINYINT(1) DEFAULT 0,
    is_claimed TINYINT(1) DEFAULT 0,
    expires_at DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_challenge (user_id, challenge_type, expires_at)
);

-- Seed default user (Mayur)
INSERT IGNORE INTO users (id, username, title, xp, level, streak, last_active)
VALUES (1, 'mayur', 'Productivity Architect', 0, 1, 0, CURRENT_DATE);

