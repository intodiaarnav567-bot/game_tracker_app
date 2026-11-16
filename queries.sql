USE game_tracker;

-- Demo with a seeded player and Hades. Rerun against the original seed data.
START TRANSACTION;
SET @player_id = 100001;
SET @game_id = 1145360;
SET @played_at = CURRENT_TIMESTAMP;

INSERT INTO User_Game (user_id, appid, ownership_status)
VALUES (@player_id, @game_id, 'owned');

INSERT INTO Gaming_Session (user_id, appid, start_time, end_time)
VALUES (@player_id, @game_id, @played_at - INTERVAL 30 MINUTE, @played_at);

INSERT INTO User_Achievement (user_id, achievement_id, appid, unlock_time)
SELECT @player_id, achievement_id, appid, @played_at
FROM Achievement
WHERE appid = @game_id
ORDER BY achievement_id
LIMIT 1;

-- Recently played games and their lifetime playtime in minutes.
SELECT g.name, l.playtime_forever AS total_minutes, l.last_played
FROM User_Library l
JOIN Game g ON g.appid = l.appid
WHERE l.user_id = @player_id AND l.last_played IS NOT NULL
ORDER BY l.last_played DESC, g.name;

-- Per-game progress, including games with zero unlocks or zero achievements.
SELECT
    g.name,
    COUNT(ua.achievement_id) AS earned,
    COUNT(a.achievement_id) AS total,
    COALESCE(ROUND(100.0 * COUNT(ua.achievement_id) / NULLIF(COUNT(a.achievement_id), 0), 1), 0)
        AS completion_percent
FROM User_Game ug
JOIN Game g ON g.appid = ug.appid
LEFT JOIN Achievement a ON a.appid = ug.appid
LEFT JOIN User_Achievement ua ON ua.user_id = ug.user_id AND ua.achievement_id = a.achievement_id
WHERE ug.user_id = @player_id AND ug.ownership_status IN ('owned', 'borrowed')
GROUP BY g.appid, g.name
ORDER BY (g.appid = @game_id) DESC, g.name;

ROLLBACK;
