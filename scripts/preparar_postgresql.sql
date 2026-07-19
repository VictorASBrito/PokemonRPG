-- Execute conectado ao banco pokemon_rpg.
ALTER DATABASE pokemon_rpg SET timezone TO 'UTC';

CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;

SELECT
    current_user,
    current_database(),
    current_setting('TimeZone') AS timezone;

SELECT extname, extversion
FROM pg_extension
WHERE extname IN ('pg_trgm', 'unaccent')
ORDER BY extname;
