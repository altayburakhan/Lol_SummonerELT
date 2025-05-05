-- Match history query for a specific summoner
SELECT *
FROM `{project_id}.{dataset_id}.matches`
WHERE EXISTS (
    SELECT 1
    FROM UNNEST(participants) as p
    WHERE p.summoner_name = @summoner_name
)
ORDER BY game_duration DESC
LIMIT @limit;

-- Average performance metrics for a summoner
SELECT 
    p.summoner_name,
    AVG(p.kda_ratio) as avg_kda,
    AVG(p.gold_per_minute) as avg_gold_per_minute,
    AVG(p.damage_per_minute) as avg_damage_per_minute,
    AVG(p.vision_score_per_minute) as avg_vision_score_per_minute,
    COUNT(*) as total_matches,
    SUM(CASE WHEN p.win = true THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as win_rate
FROM `{project_id}.{dataset_id}.matches` m,
UNNEST(m.participants) p
WHERE p.summoner_name = @summoner_name
GROUP BY p.summoner_name;

-- Champion performance for a summoner
SELECT 
    p.champion_name,
    COUNT(*) as total_games,
    AVG(p.kda_ratio) as avg_kda,
    AVG(p.gold_per_minute) as avg_gold_per_minute,
    SUM(CASE WHEN p.win = true THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as win_rate
FROM `{project_id}.{dataset_id}.matches` m,
UNNEST(m.participants) p
WHERE p.summoner_name = @summoner_name
GROUP BY p.champion_name
ORDER BY total_games DESC;

-- Recent performance trend
SELECT 
    m.match_id,
    m.game_duration,
    p.kda_ratio,
    p.gold_per_minute,
    p.damage_per_minute,
    p.vision_score_per_minute,
    p.win
FROM `{project_id}.{dataset_id}.matches` m,
UNNEST(m.participants) p
WHERE p.summoner_name = @summoner_name
ORDER BY m.game_duration DESC
LIMIT @limit; 