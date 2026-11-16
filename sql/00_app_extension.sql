USE game_tracker;
CREATE TABLE IF NOT EXISTS App_Account (
 account_id BIGINT AUTO_INCREMENT PRIMARY KEY,
 username VARCHAR(100) NOT NULL UNIQUE,
 email VARCHAR(255) NOT NULL UNIQUE,
 password_hash VARCHAR(255) NOT NULL,
 role ENUM('gamer','game_publisher','admin') NOT NULL,
 user_id BIGINT UNIQUE,
 publisher_id INT,
 is_active BOOLEAN NOT NULL DEFAULT TRUE,
 created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 last_login_at DATETIME,
 FOREIGN KEY(user_id) REFERENCES User(user_id) ON DELETE CASCADE,
 FOREIGN KEY(publisher_id) REFERENCES Publisher(publisher_id) ON DELETE RESTRICT,
 CHECK(role <> 'gamer' OR user_id IS NOT NULL),
 CHECK(role <> 'game_publisher' OR publisher_id IS NOT NULL)
);
CREATE TABLE IF NOT EXISTS App_Lock (lock_id INT PRIMARY KEY);
INSERT IGNORE INTO App_Lock VALUES(1);
-- Reset publisher privileges to remove the original catalog-wide write grants.
REVOKE ALL PRIVILEGES, GRANT OPTION FROM 'game_publisher_role';

GRANT SELECT ON game_tracker.Game TO 'game_publisher_role';

GRANT SELECT ON game_tracker.Developer TO 'game_publisher_role';

GRANT SELECT ON game_tracker.Publisher TO 'game_publisher_role';

GRANT SELECT ON game_tracker.Genre TO 'game_publisher_role';

GRANT SELECT ON game_tracker.Category TO 'game_publisher_role';

GRANT SELECT ON game_tracker.Platform TO 'game_publisher_role';

GRANT SELECT ON game_tracker.Game_Developer TO 'game_publisher_role';

GRANT SELECT ON game_tracker.Game_Publisher TO 'game_publisher_role';

GRANT SELECT ON game_tracker.Game_Genre TO 'game_publisher_role';

GRANT SELECT ON game_tracker.Game_Category TO 'game_publisher_role';

GRANT SELECT ON game_tracker.Game_Platform TO 'game_publisher_role';

GRANT SELECT ON game_tracker.Achievement TO 'game_publisher_role';

GRANT SELECT ON game_tracker.Review TO 'game_publisher_role';

GRANT SELECT ON game_tracker.Review_Vote TO 'game_publisher_role';

GRANT SELECT ON game_tracker.User_Public TO 'game_publisher_role';

DROP PROCEDURE IF EXISTS sp_purchase_game;
DELIMITER //
CREATE PROCEDURE sp_purchase_game(IN p_user_id BIGINT, IN p_appid INT) SQL SECURITY DEFINER
BEGIN
DECLARE v_lock BIGINT;
DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;
START TRANSACTION;
SELECT user_id INTO v_lock FROM User WHERE user_id=p_user_id FOR UPDATE;
IF NOT EXISTS(SELECT 1 FROM Game WHERE appid=p_appid AND is_active=1) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='This game is unavailable.'; END IF;

IF NOT EXISTS(SELECT 1 FROM User_Game WHERE user_id=p_user_id AND appid=p_appid AND ownership_status='owned') THEN
 INSERT INTO Purchase(user_id,appid,price_paid,currency) SELECT p_user_id,appid,price,currency FROM Game WHERE appid=p_appid;
 INSERT INTO User_Game(user_id,appid,ownership_status) VALUES(p_user_id,p_appid,'owned')
 ON DUPLICATE KEY UPDATE ownership_status='owned';
END IF;
COMMIT;
END//
DELIMITER ;

GRANT EXECUTE ON PROCEDURE game_tracker.sp_purchase_game TO 'gamer_role';

DROP PROCEDURE IF EXISTS sp_set_ownership;
DELIMITER //
CREATE PROCEDURE sp_set_ownership(IN p_user_id BIGINT, IN p_appid INT, IN p_status VARCHAR(30)) SQL SECURITY DEFINER
BEGIN
DECLARE v_lock BIGINT;
DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;
START TRANSACTION;
SELECT user_id INTO v_lock FROM User WHERE user_id=p_user_id FOR UPDATE;
IF p_status NOT IN ('wishlist','removed','owned') THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Choose a valid library status.'; END IF;

IF p_status='owned' THEN
IF NOT EXISTS(SELECT 1 FROM Game WHERE appid=p_appid AND is_active=1 AND is_free=1) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Use Buy to add this game.'; END IF;

END IF;
IF p_status='wishlist' THEN
IF NOT EXISTS(SELECT 1 FROM Game WHERE appid=p_appid AND is_active=1) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='This game is unavailable.'; END IF;
IF EXISTS(SELECT 1 FROM User_Game WHERE user_id=p_user_id AND appid=p_appid AND ownership_status IN ('owned','borrowed')) OR EXISTS(SELECT 1 FROM User_Achievement WHERE user_id=p_user_id AND appid=p_appid) OR EXISTS(SELECT 1 FROM Gaming_Session WHERE user_id=p_user_id AND appid=p_appid) OR EXISTS(SELECT 1 FROM Purchase WHERE user_id=p_user_id AND appid=p_appid) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='This game already has library history.'; END IF;

END IF;
IF p_status='removed' THEN
 UPDATE Gaming_Session SET end_time=CURRENT_TIMESTAMP WHERE user_id=p_user_id AND appid=p_appid AND end_time IS NULL;
 UPDATE User_Game SET ownership_status='removed' WHERE user_id=p_user_id AND appid=p_appid;
ELSE
 INSERT INTO User_Game(user_id,appid,ownership_status) VALUES(p_user_id,p_appid,p_status)
 ON DUPLICATE KEY UPDATE ownership_status=p_status;
END IF;
COMMIT;
END//
DELIMITER ;

GRANT EXECUTE ON PROCEDURE game_tracker.sp_set_ownership TO 'gamer_role';

DROP PROCEDURE IF EXISTS sp_start_session;
DELIMITER //
CREATE PROCEDURE sp_start_session(IN p_user_id BIGINT, IN p_appid INT) SQL SECURITY DEFINER
BEGIN
DECLARE v_lock BIGINT;
DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;
START TRANSACTION;
SELECT user_id INTO v_lock FROM User WHERE user_id=p_user_id FOR UPDATE;
IF NOT EXISTS(SELECT 1 FROM User_Game WHERE user_id=p_user_id AND appid=p_appid AND ownership_status IN ('owned','borrowed')) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Add this game to your Library first.'; END IF;
IF EXISTS(SELECT 1 FROM Gaming_Session WHERE user_id=p_user_id AND end_time IS NULL) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='End your current session first.'; END IF;
INSERT INTO Gaming_Session(user_id,appid,start_time) VALUES(p_user_id,p_appid,CURRENT_TIMESTAMP);
COMMIT;
END//
DELIMITER ;

GRANT EXECUTE ON PROCEDURE game_tracker.sp_start_session TO 'gamer_role';

DROP PROCEDURE IF EXISTS sp_end_session;
DELIMITER //
CREATE PROCEDURE sp_end_session(IN p_user_id BIGINT, IN p_appid INT) SQL SECURITY DEFINER
BEGIN
DECLARE v_lock BIGINT;
DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;
START TRANSACTION;
SELECT user_id INTO v_lock FROM User WHERE user_id=p_user_id FOR UPDATE;
UPDATE Gaming_Session SET end_time=CURRENT_TIMESTAMP WHERE user_id=p_user_id AND appid=p_appid AND end_time IS NULL;
COMMIT;
END//
DELIMITER ;

GRANT EXECUTE ON PROCEDURE game_tracker.sp_end_session TO 'gamer_role';

DROP PROCEDURE IF EXISTS sp_unlock_achievement;
DELIMITER //
CREATE PROCEDURE sp_unlock_achievement(IN p_user_id BIGINT, IN p_appid INT, IN p_achievement_id INT) SQL SECURITY DEFINER
BEGIN
DECLARE v_lock BIGINT;
DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;
START TRANSACTION;
SELECT user_id INTO v_lock FROM User WHERE user_id=p_user_id FOR UPDATE;
IF NOT EXISTS(SELECT 1 FROM User_Game WHERE user_id=p_user_id AND appid=p_appid AND ownership_status <> 'wishlist') THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Wishlist games cannot earn achievements.'; END IF;
IF NOT EXISTS(SELECT 1 FROM Achievement WHERE achievement_id=p_achievement_id AND appid=p_appid) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Choose an achievement for this game.'; END IF;
INSERT INTO User_Achievement(user_id,achievement_id,appid) VALUES(p_user_id,p_achievement_id,p_appid)
ON DUPLICATE KEY UPDATE unlock_time=unlock_time;
COMMIT;
END//
DELIMITER ;

GRANT EXECUTE ON PROCEDURE game_tracker.sp_unlock_achievement TO 'gamer_role';

DROP PROCEDURE IF EXISTS sp_post_review;
DELIMITER //
CREATE PROCEDURE sp_post_review(IN p_user_id BIGINT, IN p_appid INT, IN p_text TEXT, IN p_recommended BOOLEAN) SQL SECURITY DEFINER
BEGIN
DECLARE v_lock BIGINT;
DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;
START TRANSACTION;
SELECT user_id INTO v_lock FROM User WHERE user_id=p_user_id FOR UPDATE;
IF NOT EXISTS(SELECT 1 FROM User_Game WHERE user_id=p_user_id AND appid=p_appid AND ownership_status <> 'wishlist') THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Add this game to your Library first.'; END IF;
IF p_text IS NULL OR LENGTH(TRIM(p_text))=0 THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Write a review first.'; END IF;
INSERT INTO Review(user_id,appid,review_text,recommended,playtime_at_review)
SELECT p_user_id,p_appid,p_text,p_recommended,playtime_forever FROM User_Library WHERE user_id=p_user_id AND appid=p_appid
ON DUPLICATE KEY UPDATE review_text=p_text,recommended=p_recommended,review_date=CURRENT_TIMESTAMP;
COMMIT;
END//
DELIMITER ;

GRANT EXECUTE ON PROCEDURE game_tracker.sp_post_review TO 'gamer_role';

DROP PROCEDURE IF EXISTS sp_vote_review;
DELIMITER //
CREATE PROCEDURE sp_vote_review(IN p_user_id BIGINT, IN p_review_id INT, IN p_helpful BOOLEAN) SQL SECURITY DEFINER
BEGIN



IF NOT EXISTS(SELECT 1 FROM Review WHERE review_id=p_review_id AND user_id<>p_user_id) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='You can vote on another player''s review.'; END IF;
INSERT INTO Review_Vote(review_id,user_id,is_helpful) VALUES(p_review_id,p_user_id,p_helpful)
ON DUPLICATE KEY UPDATE is_helpful=p_helpful,voted_at=CURRENT_TIMESTAMP;

END//
DELIMITER ;

GRANT EXECUTE ON PROCEDURE game_tracker.sp_vote_review TO 'gamer_role';

DROP PROCEDURE IF EXISTS sp_update_profile;
DELIMITER //
CREATE PROCEDURE sp_update_profile(IN p_user_id BIGINT, IN p_username VARCHAR(100), IN p_url VARCHAR(500)) SQL SECURITY DEFINER
BEGIN



IF LENGTH(TRIM(p_username))=0 THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Enter a username.'; END IF;
UPDATE User SET username=TRIM(p_username),profile_url=p_url WHERE user_id=p_user_id;

END//
DELIMITER ;

GRANT EXECUTE ON PROCEDURE game_tracker.sp_update_profile TO 'gamer_role';

DROP PROCEDURE IF EXISTS sp_my_library;
DELIMITER //
CREATE PROCEDURE sp_my_library(IN p_user_id BIGINT) SQL SECURITY DEFINER
BEGIN



SELECT g.*,l.* FROM User_Library l JOIN Game g USING(appid) WHERE l.user_id=p_user_id ORDER BY g.name;

END//
DELIMITER ;

GRANT EXECUTE ON PROCEDURE game_tracker.sp_my_library TO 'gamer_role';

DROP PROCEDURE IF EXISTS sp_my_sessions;
DELIMITER //
CREATE PROCEDURE sp_my_sessions(IN p_user_id BIGINT) SQL SECURITY DEFINER
BEGIN



SELECT * FROM Gaming_Session WHERE user_id=p_user_id ORDER BY start_time DESC;

END//
DELIMITER ;

GRANT EXECUTE ON PROCEDURE game_tracker.sp_my_sessions TO 'gamer_role';

DROP PROCEDURE IF EXISTS sp_my_achievements;
DELIMITER //
CREATE PROCEDURE sp_my_achievements(IN p_user_id BIGINT) SQL SECURITY DEFINER
BEGIN



SELECT a.*,ua.unlock_time FROM User_Game ug JOIN Achievement a USING(appid)
 LEFT JOIN User_Achievement ua ON ua.achievement_id=a.achievement_id AND ua.user_id=ug.user_id
 WHERE ug.user_id=p_user_id AND ug.ownership_status <> 'wishlist';

END//
DELIMITER ;

GRANT EXECUTE ON PROCEDURE game_tracker.sp_my_achievements TO 'gamer_role';

DROP PROCEDURE IF EXISTS sp_my_purchases;
DELIMITER //
CREATE PROCEDURE sp_my_purchases(IN p_user_id BIGINT) SQL SECURITY DEFINER
BEGIN



SELECT p.*,g.name FROM Purchase p JOIN Game g USING(appid) WHERE user_id=p_user_id ORDER BY purchased_at DESC;

END//
DELIMITER ;

GRANT EXECUTE ON PROCEDURE game_tracker.sp_my_purchases TO 'gamer_role';

DROP PROCEDURE IF EXISTS sp_pub_my_games;
DELIMITER //
CREATE PROCEDURE sp_pub_my_games(IN p_publisher_id INT) SQL SECURITY DEFINER
BEGIN



SELECT g.* FROM Game g JOIN Game_Publisher gp USING(appid) WHERE gp.publisher_id=p_publisher_id ORDER BY g.name;

END//
DELIMITER ;

GRANT EXECUTE ON PROCEDURE game_tracker.sp_pub_my_games TO 'game_publisher_role';

DROP PROCEDURE IF EXISTS sp_pub_game_stats;
DELIMITER //
CREATE PROCEDURE sp_pub_game_stats(IN p_publisher_id INT) SQL SECURITY DEFINER
BEGIN



SELECT s.* FROM Publisher_Game_Stats s JOIN Game_Publisher gp USING(appid) WHERE gp.publisher_id=p_publisher_id;

END//
DELIMITER ;

GRANT EXECUTE ON PROCEDURE game_tracker.sp_pub_game_stats TO 'game_publisher_role';

DROP PROCEDURE IF EXISTS sp_pub_game_reviews;
DELIMITER //
CREATE PROCEDURE sp_pub_game_reviews(IN p_publisher_id INT, IN p_appid INT) SQL SECURITY DEFINER
BEGIN



IF NOT EXISTS(SELECT 1 FROM Game_Publisher WHERE publisher_id=p_publisher_id AND appid=p_appid) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='This game belongs to another publisher.'; END IF;
SELECT r.*,u.username FROM Review r JOIN User_Public u USING(user_id) WHERE appid=p_appid ORDER BY review_date DESC;

END//
DELIMITER ;

GRANT EXECUTE ON PROCEDURE game_tracker.sp_pub_game_reviews TO 'game_publisher_role';

DROP PROCEDURE IF EXISTS sp_pub_set_active;
DELIMITER //
CREATE PROCEDURE sp_pub_set_active(IN p_publisher_id INT, IN p_appid INT, IN p_active BOOLEAN) SQL SECURITY DEFINER
BEGIN



IF NOT EXISTS(SELECT 1 FROM Game_Publisher WHERE publisher_id=p_publisher_id AND appid=p_appid) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='This game belongs to another publisher.'; END IF;
UPDATE Game SET is_active=p_active WHERE appid=p_appid;

END//
DELIMITER ;

GRANT EXECUTE ON PROCEDURE game_tracker.sp_pub_set_active TO 'game_publisher_role';

DROP PROCEDURE IF EXISTS sp_pub_upsert_achievement;
DELIMITER //
CREATE PROCEDURE sp_pub_upsert_achievement(IN p_publisher_id INT, IN p_appid INT, IN p_id INT, IN p_name VARCHAR(200), IN p_description TEXT, IN p_points INT, IN p_hidden BOOLEAN) SQL SECURITY DEFINER
BEGIN



IF NOT EXISTS(SELECT 1 FROM Game_Publisher WHERE publisher_id=p_publisher_id AND appid=p_appid) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='This game belongs to another publisher.'; END IF;
IF p_points<0 OR LENGTH(TRIM(p_name))=0 THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Enter a name and nonnegative points.'; END IF;

IF p_id IS NULL THEN
 INSERT INTO Achievement(appid,achievement_name,description,points,hidden) VALUES(p_appid,p_name,p_description,p_points,p_hidden);
ELSE
IF NOT EXISTS(SELECT 1 FROM Achievement WHERE achievement_id=p_id AND appid=p_appid) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Choose an achievement for this game.'; END IF;
UPDATE Achievement SET achievement_name=p_name,description=p_description,points=p_points,hidden=p_hidden WHERE achievement_id=p_id AND appid=p_appid;
END IF;

END//
DELIMITER ;

GRANT EXECUTE ON PROCEDURE game_tracker.sp_pub_upsert_achievement TO 'game_publisher_role';

DROP PROCEDURE IF EXISTS sp_pub_delete_achievement;
DELIMITER //
CREATE PROCEDURE sp_pub_delete_achievement(IN p_publisher_id INT, IN p_appid INT, IN p_id INT) SQL SECURITY DEFINER
BEGIN



IF NOT EXISTS(SELECT 1 FROM Game_Publisher WHERE publisher_id=p_publisher_id AND appid=p_appid) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='This game belongs to another publisher.'; END IF;
DELETE FROM Achievement WHERE appid=p_appid AND achievement_id=p_id;

END//
DELIMITER ;

GRANT EXECUTE ON PROCEDURE game_tracker.sp_pub_delete_achievement TO 'game_publisher_role';

DROP PROCEDURE IF EXISTS sp_pub_update_game;
DELIMITER //
CREATE PROCEDURE sp_pub_update_game(IN p_publisher_id INT, IN p_appid INT, IN p_data JSON) SQL SECURITY DEFINER
BEGIN

DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;
START TRANSACTION;
IF NOT EXISTS(SELECT 1 FROM Game_Publisher WHERE publisher_id=p_publisher_id AND appid=p_appid) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='This game belongs to another publisher.'; END IF;
IF JSON_EXTRACT(p_data,'$.price')<0 OR (JSON_EXTRACT(p_data,'$.is_free')=1 AND JSON_EXTRACT(p_data,'$.price')<>0) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Free games must have a zero price.'; END IF;
IF LENGTH(TRIM(JSON_UNQUOTE(JSON_EXTRACT(p_data,'$.name'))))=0 THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Enter a game name.'; END IF;
UPDATE Game SET name=JSON_UNQUOTE(JSON_EXTRACT(p_data,'$.name')),short_description=JSON_UNQUOTE(JSON_EXTRACT(p_data,'$.short_description')),price=CAST(JSON_UNQUOTE(JSON_EXTRACT(p_data,'$.price')) AS DECIMAL(10,2)),currency=JSON_UNQUOTE(JSON_EXTRACT(p_data,'$.currency')),release_date=NULLIF(JSON_UNQUOTE(JSON_EXTRACT(p_data,'$.release_date')),''),required_age=CAST(JSON_EXTRACT(p_data,'$.required_age') AS UNSIGNED),is_free=CAST(JSON_EXTRACT(p_data,'$.is_free') AS UNSIGNED),header_image_url=JSON_UNQUOTE(JSON_EXTRACT(p_data,'$.header_image_url')) WHERE appid=p_appid;
DELETE FROM Game_Genre WHERE appid=p_appid;
INSERT INTO Game_Genre(appid,genre_id)
SELECT p_appid,j.id FROM JSON_TABLE(p_data,'$.genres[*]' COLUMNS(id INT PATH '$')) j;
DELETE FROM Game_Category WHERE appid=p_appid;
INSERT INTO Game_Category(appid,category_id)
SELECT p_appid,j.id FROM JSON_TABLE(p_data,'$.categories[*]' COLUMNS(id INT PATH '$')) j;
DELETE FROM Game_Platform WHERE appid=p_appid;
INSERT INTO Game_Platform(appid,platform_id)
SELECT p_appid,j.id FROM JSON_TABLE(p_data,'$.platforms[*]' COLUMNS(id INT PATH '$')) j;
DELETE FROM Game_Developer WHERE appid=p_appid;
INSERT INTO Game_Developer(appid,developer_id)
SELECT p_appid,j.id FROM JSON_TABLE(p_data,'$.developers[*]' COLUMNS(id INT PATH '$')) j;
IF LENGTH(TRIM(COALESCE(JSON_UNQUOTE(JSON_EXTRACT(p_data,'$.new_developer')),'')))>0 THEN
 INSERT INTO Developer(developer_name) VALUES(TRIM(JSON_UNQUOTE(JSON_EXTRACT(p_data,'$.new_developer')))) ON DUPLICATE KEY UPDATE developer_id=LAST_INSERT_ID(developer_id);
 INSERT IGNORE INTO Game_Developer VALUES(p_appid,LAST_INSERT_ID());
END IF;

COMMIT;
END//
DELIMITER ;

GRANT EXECUTE ON PROCEDURE game_tracker.sp_pub_update_game TO 'game_publisher_role';

DROP PROCEDURE IF EXISTS sp_pub_create_game;
DELIMITER //
CREATE PROCEDURE sp_pub_create_game(IN p_publisher_id INT, IN p_data JSON) SQL SECURITY DEFINER
BEGIN
DECLARE p_appid INT; DECLARE v_lock INT;
DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;
START TRANSACTION;
SELECT lock_id INTO v_lock FROM App_Lock WHERE lock_id=1 FOR UPDATE;
SELECT COALESCE(MAX(appid),0)+1 INTO p_appid FROM Game;
IF JSON_EXTRACT(p_data,'$.price')<0 OR (JSON_EXTRACT(p_data,'$.is_free')=1 AND JSON_EXTRACT(p_data,'$.price')<>0) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Free games must have a zero price.'; END IF;
IF LENGTH(TRIM(JSON_UNQUOTE(JSON_EXTRACT(p_data,'$.name'))))=0 THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Enter a game name.'; END IF;
INSERT INTO Game(appid,name,short_description,price,currency,release_date,required_age,is_free,header_image_url) VALUES(p_appid,JSON_UNQUOTE(JSON_EXTRACT(p_data,'$.name')),JSON_UNQUOTE(JSON_EXTRACT(p_data,'$.short_description')),CAST(JSON_UNQUOTE(JSON_EXTRACT(p_data,'$.price')) AS DECIMAL(10,2)),JSON_UNQUOTE(JSON_EXTRACT(p_data,'$.currency')),NULLIF(JSON_UNQUOTE(JSON_EXTRACT(p_data,'$.release_date')),''),CAST(JSON_EXTRACT(p_data,'$.required_age') AS UNSIGNED),CAST(JSON_EXTRACT(p_data,'$.is_free') AS UNSIGNED),JSON_UNQUOTE(JSON_EXTRACT(p_data,'$.header_image_url')));
INSERT INTO Game_Publisher VALUES(p_appid,p_publisher_id);
DELETE FROM Game_Genre WHERE appid=p_appid;
INSERT INTO Game_Genre(appid,genre_id)
SELECT p_appid,j.id FROM JSON_TABLE(p_data,'$.genres[*]' COLUMNS(id INT PATH '$')) j;
DELETE FROM Game_Category WHERE appid=p_appid;
INSERT INTO Game_Category(appid,category_id)
SELECT p_appid,j.id FROM JSON_TABLE(p_data,'$.categories[*]' COLUMNS(id INT PATH '$')) j;
DELETE FROM Game_Platform WHERE appid=p_appid;
INSERT INTO Game_Platform(appid,platform_id)
SELECT p_appid,j.id FROM JSON_TABLE(p_data,'$.platforms[*]' COLUMNS(id INT PATH '$')) j;
DELETE FROM Game_Developer WHERE appid=p_appid;
INSERT INTO Game_Developer(appid,developer_id)
SELECT p_appid,j.id FROM JSON_TABLE(p_data,'$.developers[*]' COLUMNS(id INT PATH '$')) j;
IF LENGTH(TRIM(COALESCE(JSON_UNQUOTE(JSON_EXTRACT(p_data,'$.new_developer')),'')))>0 THEN
 INSERT INTO Developer(developer_name) VALUES(TRIM(JSON_UNQUOTE(JSON_EXTRACT(p_data,'$.new_developer')))) ON DUPLICATE KEY UPDATE developer_id=LAST_INSERT_ID(developer_id);
 INSERT IGNORE INTO Game_Developer VALUES(p_appid,LAST_INSERT_ID());
END IF;
SELECT p_appid AS appid;
COMMIT;
END//
DELIMITER ;

GRANT EXECUTE ON PROCEDURE game_tracker.sp_pub_create_game TO 'game_publisher_role';
