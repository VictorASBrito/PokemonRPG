SELECT tablename
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;

SELECT COUNT(*) AS quantidade_tabelas
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename <> 'alembic_version';

SELECT version_num
FROM alembic_version;

SELECT
    tc.table_name,
    tc.constraint_name,
    tc.constraint_type
FROM information_schema.table_constraints tc
WHERE tc.table_schema = 'public'
ORDER BY tc.table_name, tc.constraint_type, tc.constraint_name;
