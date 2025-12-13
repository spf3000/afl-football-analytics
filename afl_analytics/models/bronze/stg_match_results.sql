-- Bronze Layer: Match Results
-- Pure function: raw file → typed, timestamped table
-- Idempotent: Can run multiple times safely

{{ config(
    materialized='table',
    tags=['bronze', 'match_data']
) }}

WITH all_files_raw AS (
    SELECT *
    FROM read_files(
        '/Volumes/afl_analytics_dev/raw/afl_raw_files/real_afl_attendance_*.txt',
        format => 'text',
        header => false
    )
),

cleaned AS (
    SELECT
        current_timestamp() as _loaded_at,
        '_volume_files' as _source_system,
        
        -- Extract year from filename if needed
        CAST(REGEXP_EXTRACT(_metadata.file_path, 'real_afl_attendance_(\\d{4})', 1) AS INT) as season,
        
        -- Your cleaning logic here
        
    FROM all_files_raw
)

SELECT * FROM cleaned
