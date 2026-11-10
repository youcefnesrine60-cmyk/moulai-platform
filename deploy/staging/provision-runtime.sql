-- REVIEW ONLY: apply after explicit activation approval, on the isolated project.
-- The runtime login must first be created with a private unique secret; none is embedded here.
DO $attest$
BEGIN
  IF current_database() IS DISTINCT FROM 'moulai_staging_rehearsal'
    OR current_user IS DISTINCT FROM 'moulai_staging_migrator'
    OR current_setting('neon.project_id',true) IS DISTINCT FROM 'sparkling-rice-23028300'
    OR current_setting('neon.branch_id',true) IS DISTINCT FROM 'br-lucky-smoke-b9edyxoe'
    OR current_setting('neon.endpoint_id',true) IS DISTINCT FROM 'ep-odd-wildflower-b9wacgg0'
    OR (SELECT version_num FROM public.alembic_version) IS DISTINCT FROM 'o420261108'
  THEN RAISE EXCEPTION 'staging_runtime_target_refused'; END IF;
  IF NOT EXISTS(SELECT 1 FROM pg_roles WHERE rolname='moulai_staging_app'
    AND rolcanlogin AND NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole)
    OR pg_has_role('moulai_staging_app','moulai_staging_migrator','MEMBER')
  THEN RAISE EXCEPTION 'staging_limited_runtime_role_required'; END IF;
END $attest$;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO moulai_staging_app;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO moulai_staging_app;
GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA public TO moulai_staging_app;
DO $grants$
DECLARE table_name text;
BEGIN
  FOR table_name IN SELECT tablename FROM pg_tables
    WHERE schemaname='public' AND tablename<>'alembic_version'
  LOOP
    EXECUTE format('GRANT INSERT,UPDATE,DELETE ON public.%I TO moulai_staging_app',table_name);
  END LOOP;
END $grants$;
-- No table ownership, schema CREATE, migration-history write, personal admin or cash grant.
