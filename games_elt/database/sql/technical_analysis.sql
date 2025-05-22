-- Calculate RSI for KDA ratio
WITH kda_changes AS (
    SELECT 
        match_id,
        game_duration,
        kda_ratio,
        LAG(kda_ratio) OVER (ORDER BY game_duration) as prev_kda
    FROM `{project_id}.{dataset_id}.matches` m,
    UNNEST(m.participants) p
    WHERE p.summoner_name = @summoner_name
),
kda_gains_losses AS (
    SELECT 
        match_id,
        game_duration,
        kda_ratio,
        CASE 
            WHEN kda_ratio > prev_kda THEN kda_ratio - prev_kda 
            ELSE 0 
        END as gain,
        CASE 
            WHEN kda_ratio < prev_kda THEN prev_kda - kda_ratio 
            ELSE 0 
        END as loss
    FROM kda_changes
    WHERE prev_kda IS NOT NULL
),
avg_gains_losses AS (
    SELECT 
        match_id,
        game_duration,
        kda_ratio,
        AVG(gain) OVER (ORDER BY game_duration ROWS BETWEEN 13 PRECEDING AND CURRENT ROW) as avg_gain,
        AVG(loss) OVER (ORDER BY game_duration ROWS BETWEEN 13 PRECEDING AND CURRENT ROW) as avg_loss
    FROM kda_gains_losses
)
SELECT 
    match_id,
    game_duration,
    kda_ratio,
    100 - (100 / (1 + avg_gain / NULLIF(avg_loss, 0))) as rsi
FROM avg_gains_losses
WHERE avg_gain IS NOT NULL AND avg_loss IS NOT NULL
ORDER BY game_duration DESC;

-- Calculate Bollinger Bands for Gold per Minute
WITH gold_stats AS (
    SELECT 
        match_id,
        game_duration,
        gold_per_minute,
        AVG(gold_per_minute) OVER (ORDER BY game_duration ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) as ma,
        STDDEV(gold_per_minute) OVER (ORDER BY game_duration ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) as std
    FROM `{project_id}.{dataset_id}.matches` m,
    UNNEST(m.participants) p
    WHERE p.summoner_name = @summoner_name
)
SELECT 
    match_id,
    game_duration,
    gold_per_minute,
    ma as middle_band,
    ma + (2 * std) as upper_band,
    ma - (2 * std) as lower_band
FROM gold_stats
WHERE ma IS NOT NULL AND std IS NOT NULL
ORDER BY game_duration DESC;

-- Performance by Game Mode
SELECT 
    m.game_mode,
    COUNT(*) as total_games,
    AVG(p.kda_ratio) as avg_kda,
    AVG(p.gold_per_minute) as avg_gold_per_minute,
    AVG(p.damage_per_minute) as avg_damage_per_minute,
    SUM(CASE WHEN p.win = true THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as win_rate
FROM `{project_id}.{dataset_id}.matches` m,
UNNEST(m.participants) p
WHERE p.summoner_name = @summoner_name
GROUP BY m.game_mode
ORDER BY total_games DESC; 