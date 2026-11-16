-- game_tracker_role_setup.sql (revised)
-- Target: MySQL 8.0+ (roles supported)
-- Run as a DBA/admin account AFTER schema.sql (it needs the tables and views).
--
USE game_tracker;

-- 1) Create database roles
CREATE ROLE IF NOT EXISTS 'gamer_role', 'admin_role', 'game_publisher_role';

-- 2) GAMER: read-only access to the public catalog, reviews and public profiles.
-- Writes to personal records (library, reviews, votes, sessions) should go through the
-- application/API or SQL SECURITY DEFINER procedures that verify the logged-in
-- account owns user_id. Table-level grants cannot limit writes to a user's own rows.
GRANT SELECT ON game_tracker.Game TO 'gamer_role';
GRANT SELECT ON game_tracker.Developer TO 'gamer_role';
GRANT SELECT ON game_tracker.Publisher TO 'gamer_role';
GRANT SELECT ON game_tracker.Genre TO 'gamer_role';
GRANT SELECT ON game_tracker.Category TO 'gamer_role';
GRANT SELECT ON game_tracker.Platform TO 'gamer_role';
GRANT SELECT ON game_tracker.Game_Developer TO 'gamer_role';
GRANT SELECT ON game_tracker.Game_Publisher TO 'gamer_role';
GRANT SELECT ON game_tracker.Game_Genre TO 'gamer_role';
GRANT SELECT ON game_tracker.Game_Category TO 'gamer_role';
GRANT SELECT ON game_tracker.Game_Platform TO 'gamer_role';
GRANT SELECT ON game_tracker.Achievement TO 'gamer_role';
GRANT SELECT ON game_tracker.Review TO 'gamer_role';
GRANT SELECT ON game_tracker.Review_Vote TO 'gamer_role';
GRANT SELECT ON game_tracker.User_Public TO 'gamer_role';

-- 3) ADMIN: read and modify records in this database, but no account/role
-- administration and no schema DDL. Keep MySQL DBA credentials separate.
-- Note: this includes User_Account (email, password_hash) and Purchase.
GRANT SELECT, INSERT, UPDATE, DELETE ON game_tracker.* TO 'admin_role';

-- 4) GAME PUBLISHER: read the catalog, public reviews and aggregate stats.
-- Manage catalog metadata and achievements. The role grants catalog-wide access.
-- An application can use Game_Publisher to restrict edits to assigned games.
-- Catalog reads
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
-- Public/aggregate data about players (no private tables)
GRANT SELECT ON game_tracker.Review TO 'game_publisher_role';
GRANT SELECT ON game_tracker.Review_Vote TO 'game_publisher_role';
GRANT SELECT ON game_tracker.User_Public TO 'game_publisher_role';
GRANT SELECT ON game_tracker.Publisher_Game_Stats TO 'game_publisher_role';
-- Catalog writes (no DELETE on games or shared reference tables)
GRANT INSERT, UPDATE ON game_tracker.Game TO 'game_publisher_role';
GRANT INSERT ON game_tracker.Developer TO 'game_publisher_role';
GRANT INSERT ON game_tracker.Publisher TO 'game_publisher_role';
GRANT INSERT, UPDATE, DELETE ON game_tracker.Game_Developer TO 'game_publisher_role';
GRANT INSERT, UPDATE, DELETE ON game_tracker.Game_Publisher TO 'game_publisher_role';
GRANT INSERT, UPDATE, DELETE ON game_tracker.Game_Genre TO 'game_publisher_role';
GRANT INSERT, UPDATE, DELETE ON game_tracker.Game_Category TO 'game_publisher_role';
GRANT INSERT, UPDATE, DELETE ON game_tracker.Game_Platform TO 'game_publisher_role';
GRANT INSERT, UPDATE, DELETE ON game_tracker.Achievement TO 'game_publisher_role';

-- 5) Template: create logins and activate roles (edit names, hosts and passwords,
-- then uncomment). Roles do nothing until they are granted AND activated.
-- CREATE USER IF NOT EXISTS 'app_gamer'@'10.0.0.%'     IDENTIFIED BY 'CHANGE_ME';
-- GRANT 'gamer_role' TO 'app_gamer'@'10.0.0.%';
-- SET DEFAULT ROLE 'gamer_role' TO 'app_gamer'@'10.0.0.%';
--
-- CREATE USER IF NOT EXISTS 'app_publisher'@'10.0.0.%' IDENTIFIED BY 'CHANGE_ME';
-- GRANT 'game_publisher_role' TO 'app_publisher'@'10.0.0.%';
-- SET DEFAULT ROLE 'game_publisher_role' TO 'app_publisher'@'10.0.0.%';
--
-- CREATE USER IF NOT EXISTS 'app_admin'@'10.0.0.%'     IDENTIFIED BY 'CHANGE_ME';
-- GRANT 'admin_role' TO 'app_admin'@'10.0.0.%';
-- SET DEFAULT ROLE 'admin_role' TO 'app_admin'@'10.0.0.%';

-- Notes:
-- * MySQL accounts are database logins, not rows in the `User` application table.
--   Application login credentials live in User_Account (store only a bcrypt/argon2 hash).
-- * The views User_Public and Publisher_Game_Stats run with their definer's privileges
--   (SQL SECURITY DEFINER is the default), so roles can read them without access to the
--   underlying private tables. The definer is whoever ran schema.sql.
-- * The gamer role is intentionally read-only until user-specific writes are implemented
--   with ownership checks.
-- * If connecting remotely, replace the host pattern with a carefully restricted host/IP.
