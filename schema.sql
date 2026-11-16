-- Target: MySQL 8.0.16+.
-- Run this first on a fresh instance, then sample_data (1).sql.
-- Playtime is in minutes. Keep removed library entries to preserve play history.
-- User deletion is restricted when purchases exist. Delist games with is_active.

CREATE DATABASE IF NOT EXISTS game_tracker
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_0900_ai_ci;
USE game_tracker;

-- 1. USER
CREATE TABLE User (
    user_id BIGINT PRIMARY KEY,
    username VARCHAR(100) NOT NULL,
    profile_url VARCHAR(500),
    user_level INT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CHECK (user_level >= 0)
) DEFAULT CHARSET = utf8mb4;

-- 1b. USER_ACCOUNT (login credentials, kept apart from the public profile)
-- Store a salted hash from bcrypt/argon2 in password_hash. NEVER store plaintext.
CREATE TABLE User_Account (
    user_id BIGINT PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login_at DATETIME,
    FOREIGN KEY (user_id) REFERENCES User(user_id) ON DELETE CASCADE
) DEFAULT CHARSET = utf8mb4;

-- 2. GAME
CREATE TABLE Game (
    appid INT PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    release_date DATE,
    type VARCHAR(50) DEFAULT 'game',
    is_free BOOLEAN DEFAULT FALSE,
    required_age INT DEFAULT 0,
    price DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    currency CHAR(3) NOT NULL DEFAULT 'USD',
    short_description TEXT,
    header_image_url VARCHAR(500),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,   -- FALSE = delisted from the store
    CHECK (required_age >= 0),
    CHECK (price >= 0),
    CHECK (is_free = FALSE OR price = 0),
    INDEX idx_game_name (name),
    INDEX idx_game_release (release_date)
) DEFAULT CHARSET = utf8mb4;

-- 3. DEVELOPER
CREATE TABLE Developer (
    developer_id INT AUTO_INCREMENT PRIMARY KEY,
    developer_name VARCHAR(200) NOT NULL UNIQUE
) DEFAULT CHARSET = utf8mb4;

-- 4. PUBLISHER
CREATE TABLE Publisher (
    publisher_id INT AUTO_INCREMENT PRIMARY KEY,
    publisher_name VARCHAR(200) NOT NULL UNIQUE
) DEFAULT CHARSET = utf8mb4;

-- 5. GENRE
CREATE TABLE Genre (
    genre_id INT AUTO_INCREMENT PRIMARY KEY,
    genre_name VARCHAR(100) NOT NULL UNIQUE
) DEFAULT CHARSET = utf8mb4;

-- 6. CATEGORY
CREATE TABLE Category (
    category_id INT AUTO_INCREMENT PRIMARY KEY,
    category_name VARCHAR(100) NOT NULL UNIQUE
) DEFAULT CHARSET = utf8mb4;

-- 7. PLATFORM
CREATE TABLE Platform (
    platform_id INT AUTO_INCREMENT PRIMARY KEY,
    platform_name VARCHAR(50) NOT NULL UNIQUE
) DEFAULT CHARSET = utf8mb4;

-- 8. GAME_DEVELOPER
CREATE TABLE Game_Developer (
    appid INT NOT NULL,
    developer_id INT NOT NULL,
    PRIMARY KEY (appid, developer_id),
    FOREIGN KEY (appid) REFERENCES Game(appid) ON DELETE CASCADE,
    FOREIGN KEY (developer_id) REFERENCES Developer(developer_id) ON DELETE CASCADE
) DEFAULT CHARSET = utf8mb4;

-- 9. GAME_PUBLISHER
CREATE TABLE Game_Publisher (
    appid INT NOT NULL,
    publisher_id INT NOT NULL,
    PRIMARY KEY (appid, publisher_id),
    FOREIGN KEY (appid) REFERENCES Game(appid) ON DELETE CASCADE,
    FOREIGN KEY (publisher_id) REFERENCES Publisher(publisher_id) ON DELETE CASCADE
) DEFAULT CHARSET = utf8mb4;

-- 10. GAME_GENRE
CREATE TABLE Game_Genre (
    appid INT NOT NULL,
    genre_id INT NOT NULL,
    PRIMARY KEY (appid, genre_id),
    FOREIGN KEY (appid) REFERENCES Game(appid) ON DELETE CASCADE,
    FOREIGN KEY (genre_id) REFERENCES Genre(genre_id) ON DELETE CASCADE
) DEFAULT CHARSET = utf8mb4;

-- 11. GAME_CATEGORY
CREATE TABLE Game_Category (
    appid INT NOT NULL,
    category_id INT NOT NULL,
    PRIMARY KEY (appid, category_id),
    FOREIGN KEY (appid) REFERENCES Game(appid) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES Category(category_id) ON DELETE CASCADE
) DEFAULT CHARSET = utf8mb4;

-- 12. GAME_PLATFORM
CREATE TABLE Game_Platform (
    appid INT NOT NULL,
    platform_id INT NOT NULL,
    PRIMARY KEY (appid, platform_id),
    FOREIGN KEY (appid) REFERENCES Game(appid) ON DELETE CASCADE,
    FOREIGN KEY (platform_id) REFERENCES Platform(platform_id) ON DELETE CASCADE
) DEFAULT CHARSET = utf8mb4;

-- 13. USER_GAME (a user's library / wishlist)
CREATE TABLE User_Game (
    user_id BIGINT NOT NULL,
    appid INT NOT NULL,
    ownership_status VARCHAR(30) NOT NULL DEFAULT 'owned',

    PRIMARY KEY (user_id, appid),

    FOREIGN KEY (user_id) REFERENCES User(user_id) ON DELETE CASCADE,
    FOREIGN KEY (appid) REFERENCES Game(appid) ON DELETE RESTRICT,

    CHECK (
        ownership_status IN
        ('owned', 'borrowed', 'wishlist', 'removed')
    ),
    INDEX idx_user_game_appid_status (appid, ownership_status)
) DEFAULT CHARSET = utf8mb4;

-- 13b. PURCHASE (what a user paid, and when)
CREATE TABLE Purchase (
    purchase_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    appid INT NOT NULL,
    price_paid DECIMAL(10,2) NOT NULL,
    currency CHAR(3) NOT NULL DEFAULT 'USD',
    purchased_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES User(user_id) ON DELETE RESTRICT,
    FOREIGN KEY (appid) REFERENCES Game(appid) ON DELETE RESTRICT,

    CHECK (price_paid >= 0),
    INDEX idx_purchase_user_time (user_id, purchased_at),
    INDEX idx_purchase_game (appid)
) DEFAULT CHARSET = utf8mb4;

-- 14. ACHIEVEMENT
CREATE TABLE Achievement (
    achievement_id INT AUTO_INCREMENT PRIMARY KEY,
    appid INT NOT NULL,
    achievement_name VARCHAR(200) NOT NULL,
    description TEXT,
    points INT DEFAULT 0,
    hidden BOOLEAN DEFAULT FALSE,

    FOREIGN KEY (appid) REFERENCES Game(appid) ON DELETE CASCADE,
    UNIQUE (appid, achievement_name),
    UNIQUE (achievement_id, appid),
    CHECK (points >= 0)
) DEFAULT CHARSET = utf8mb4;

-- 15. USER_ACHIEVEMENT
-- A row represents an earned achievement. Missing rows represent locked achievements.
CREATE TABLE User_Achievement (
    user_id BIGINT NOT NULL,
    achievement_id INT NOT NULL,
    appid INT NOT NULL,
    unlock_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (user_id, achievement_id),

    FOREIGN KEY (user_id, appid)
        REFERENCES User_Game(user_id, appid) ON DELETE CASCADE,
    FOREIGN KEY (achievement_id, appid)
        REFERENCES Achievement(achievement_id, appid) ON DELETE CASCADE
) DEFAULT CHARSET = utf8mb4;

-- 16. REVIEW
CREATE TABLE Review (
    review_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    appid INT NOT NULL,
    review_text TEXT,
    recommended BOOLEAN NOT NULL,
    review_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    playtime_at_review INT DEFAULT 0,

    CONSTRAINT uq_review_user_game UNIQUE (user_id, appid),
    FOREIGN KEY (user_id) REFERENCES User(user_id) ON DELETE CASCADE,
    FOREIGN KEY (appid) REFERENCES Game(appid) ON DELETE RESTRICT,

    CHECK (playtime_at_review >= 0),
    INDEX idx_review_game_date (appid, review_date)
) DEFAULT CHARSET = utf8mb4;

-- 16b. REVIEW_VOTE ("was this review helpful?")
CREATE TABLE Review_Vote (
    review_id INT NOT NULL,
    user_id BIGINT NOT NULL,
    is_helpful BOOLEAN NOT NULL,
    voted_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (review_id, user_id),
    FOREIGN KEY (review_id) REFERENCES Review(review_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES User(user_id) ON DELETE CASCADE,
    INDEX idx_review_vote_user (user_id)
) DEFAULT CHARSET = utf8mb4;

-- 17. GAMING_SESSION
-- duration is in minutes and is derived from start_time/end_time by the triggers below.
CREATE TABLE Gaming_Session (
    session_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    appid INT NOT NULL,
    start_time DATETIME NOT NULL,
    end_time DATETIME,
    duration INT,

    FOREIGN KEY (user_id, appid)
        REFERENCES User_Game(user_id, appid) ON DELETE CASCADE,

    CHECK (duration IS NULL OR duration >= 0),
    CHECK (end_time IS NULL OR end_time >= start_time),
    INDEX idx_session_user_start (user_id, start_time),
    INDEX idx_session_game_start (appid, start_time)
) DEFAULT CHARSET = utf8mb4;

-- The duration of an open session is NULL.
DELIMITER //
CREATE TRIGGER trg_session_duration_ins
BEFORE INSERT ON Gaming_Session
FOR EACH ROW
BEGIN
    SET NEW.duration = TIMESTAMPDIFF(MINUTE, NEW.start_time, NEW.end_time);
END//

CREATE TRIGGER trg_session_duration_upd
BEFORE UPDATE ON Gaming_Session
FOR EACH ROW
BEGIN
    SET NEW.duration = TIMESTAMPDIFF(MINUTE, NEW.start_time, NEW.end_time);
END//

-- A removed entry can retain or receive historical unlocks.
CREATE TRIGGER trg_achievement_library_ins
BEFORE INSERT ON User_Achievement
FOR EACH ROW
BEGIN
    IF EXISTS (
        SELECT 1 FROM User_Game
        WHERE user_id = NEW.user_id AND appid = NEW.appid AND ownership_status = 'wishlist'
    ) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Wishlist games cannot earn achievements';
    END IF;
END//

CREATE TRIGGER trg_achievement_library_upd
BEFORE UPDATE ON User_Achievement
FOR EACH ROW
BEGIN
    IF (NEW.user_id <> OLD.user_id OR NEW.appid <> OLD.appid) AND EXISTS (
        SELECT 1 FROM User_Game
        WHERE user_id = NEW.user_id AND appid = NEW.appid AND ownership_status = 'wishlist'
    ) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Wishlist games cannot earn achievements';
    END IF;
END//
DELIMITER ;

-- Playtime comes from completed sessions. Recent playtime counts sessions ending
-- in the last 14 days.
CREATE VIEW User_Library AS
SELECT
    ug.user_id,
    ug.appid,
    ug.ownership_status,
    COALESCE(SUM(s.duration), 0) AS playtime_forever,
    SUM(CASE WHEN s.end_time BETWEEN CURRENT_TIMESTAMP - INTERVAL 14 DAY
                               AND CURRENT_TIMESTAMP THEN s.duration ELSE 0 END) AS playtime_2weeks,
    MAX(s.end_time) AS last_played
FROM User_Game ug
LEFT JOIN Gaming_Session s ON s.user_id = ug.user_id AND s.appid = ug.appid
GROUP BY ug.user_id, ug.appid, ug.ownership_status;

-- ---------------------------------------------------------------------------
-- VIEWS (used by the role setup so roles don't need access to private tables)
-- ---------------------------------------------------------------------------

-- Public profile: no account data, no library.
CREATE OR REPLACE VIEW User_Public AS
SELECT user_id, username, profile_url, user_level
FROM User;

-- Per-game aggregate stats for publishers. Playtime figures are in minutes.
CREATE OR REPLACE VIEW Publisher_Game_Stats AS
SELECT
    g.appid,
    g.name,
    (SELECT COUNT(*) FROM User_Game ug
      WHERE ug.appid = g.appid AND ug.ownership_status = 'owned') AS owners,
    (SELECT COUNT(*) FROM User_Game ug
      WHERE ug.appid = g.appid AND ug.ownership_status = 'wishlist') AS wishlists,
    (SELECT COALESCE(AVG(ug.playtime_forever), 0) FROM User_Library ug
      WHERE ug.appid = g.appid AND ug.ownership_status = 'owned') AS avg_playtime_minutes,
    (SELECT COUNT(*) FROM Review r WHERE r.appid = g.appid) AS review_count,
    (SELECT COALESCE(SUM(r.recommended), 0) FROM Review r
      WHERE r.appid = g.appid) AS recommended_count
FROM Game g;
