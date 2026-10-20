# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Frozen SELECT-only G1 catalog contract used by the G2 preservation verifier.

Extracted without query changes from the reviewed historical collector. This
source contains SQL definitions only, never connection details or result data.
Historical reports and collector evidence remain local and ignored by Git.
"""

# ==============================================
# ORIGINAL CATALOG FINGERPRINT QUERIES
# ==============================================

CATALOGS = {
    "columns": "SELECT c.relname AS "
    "table_name,a.attnum,a.attname,pg_catalog.format_type(a.atttypid,a.atttypmod) "
    "AS "
    "type,a.attnotnull,a.attidentity,a.attgenerated,pg_catalog.pg_get_expr(d.adbin,d.adrelid) "
    "AS default_expression FROM pg_catalog.pg_attribute a JOIN "
    "pg_catalog.pg_class c ON c.oid=a.attrelid JOIN pg_catalog.pg_namespace n "
    "ON n.oid=c.relnamespace LEFT JOIN pg_catalog.pg_attrdef d ON "
    "d.adrelid=a.attrelid AND d.adnum=a.attnum WHERE n.nspname='public' AND "
    "c.relkind IN ('r','p') AND a.attnum>0 AND NOT a.attisdropped ORDER BY "
    "c.relname,a.attnum",
    "constraints": "SELECT c.relname AS "
    "table_name,k.conname,k.contype,k.convalidated,k.condeferrable,k.condeferred,pg_catalog.pg_get_constraintdef(k.oid,true) "
    "AS definition FROM pg_catalog.pg_constraint k JOIN "
    "pg_catalog.pg_namespace n ON n.oid=k.connamespace LEFT JOIN "
    "pg_catalog.pg_class c ON c.oid=k.conrelid WHERE n.nspname='public' "
    "ORDER BY c.relname,k.conname",
    "indexes": "SELECT c.relname AS table_name,i.relname AS "
    "name,x.indisvalid,x.indisready,x.indisunique,pg_catalog.pg_get_indexdef(i.oid) "
    "AS definition FROM pg_catalog.pg_index x JOIN pg_catalog.pg_class i ON "
    "i.oid=x.indexrelid JOIN pg_catalog.pg_class c ON c.oid=x.indrelid JOIN "
    "pg_catalog.pg_namespace n ON n.oid=c.relnamespace WHERE "
    "n.nspname='public' ORDER BY c.relname,i.relname",
    "triggers": "SELECT c.relname AS "
    "table_name,t.tgname,t.tgenabled,pg_catalog.pg_get_triggerdef(t.oid,true) "
    "AS definition FROM pg_catalog.pg_trigger t JOIN pg_catalog.pg_class c ON "
    "c.oid=t.tgrelid JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace "
    "WHERE n.nspname='public' AND NOT t.tgisinternal ORDER BY "
    "c.relname,t.tgname",
    "routines": "SELECT p.proname,pg_catalog.pg_get_function_identity_arguments(p.oid) AS "
    "arguments,pg_get_userbyid(p.proowner) AS owner,p.proacl::text AS "
    "acl,md5(pg_catalog.pg_get_functiondef(p.oid)) AS definition_fingerprint "
    "FROM pg_catalog.pg_proc p JOIN pg_catalog.pg_namespace n ON "
    "n.oid=p.pronamespace WHERE n.nspname='public' ORDER BY "
    "p.proname,arguments",
    "relations": "SELECT c.relname,c.relkind,pg_get_userbyid(c.relowner) AS "
    "owner,c.relacl::text AS acl,c.relrowsecurity,c.relforcerowsecurity FROM "
    "pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON "
    "n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind IN "
    "('r','p','S','v','m','f') ORDER BY c.relname",
    "schemas": "SELECT nspname,pg_get_userbyid(nspowner) AS owner,nspacl::text AS acl "
    "FROM pg_catalog.pg_namespace WHERE nspname NOT LIKE 'pg_%' AND "
    "nspname<>'information_schema' ORDER BY nspname",
    "database_privileges": "SELECT datname,pg_get_userbyid(datdba) AS owner,datacl::text "
    "AS acl FROM pg_catalog.pg_database WHERE "
    "datname=current_database()",
    "roles": "SELECT "
    "rolname,rolsuper,rolinherit,rolcreaterole,rolcreatedb,rolcanlogin,rolreplication,rolbypassrls,rolconnlimit "
    "FROM pg_catalog.pg_roles ORDER BY rolname",
    "role_memberships": "SELECT pg_get_userbyid(roleid) AS role,pg_get_userbyid(member) "
    "AS member,pg_get_userbyid(grantor) AS "
    "grantor,admin_option,inherit_option,set_option FROM "
    "pg_catalog.pg_auth_members ORDER BY 1,2,3",
    "default_privileges": "SELECT pg_get_userbyid(d.defaclrole) AS "
    "role,COALESCE(n.nspname,'all_schemas') AS "
    "schema,d.defaclobjtype,d.defaclacl::text AS acl FROM "
    "pg_catalog.pg_default_acl d LEFT JOIN pg_catalog.pg_namespace "
    "n ON n.oid=d.defaclnamespace ORDER BY 1,2,3",
    "rls": "SELECT schemaname,tablename,policyname,permissive,roles,cmd,qual,with_check "
    "FROM pg_catalog.pg_policies WHERE schemaname='public' ORDER BY "
    "tablename,policyname",
    "sequence_definitions": "SELECT c.relname,pg_get_userbyid(c.relowner) AS "
    "owner,c.relacl::text AS acl,s.seqtypid::regtype::text AS "
    "type,s.seqstart,s.seqincrement,s.seqmax,s.seqmin,s.seqcache,s.seqcycle,COALESCE(t.relname,'') "
    "AS dependent_table,COALESCE(a.attname,'') AS "
    "dependent_column FROM pg_catalog.pg_sequence s JOIN "
    "pg_catalog.pg_class c ON c.oid=s.seqrelid JOIN "
    "pg_catalog.pg_namespace n ON n.oid=c.relnamespace LEFT JOIN "
    "pg_catalog.pg_depend d ON d.classid='pg_class'::regclass AND "
    "d.objid=c.oid AND d.deptype IN ('a','i') LEFT JOIN "
    "pg_catalog.pg_class t ON t.oid=d.refobjid LEFT JOIN "
    "pg_catalog.pg_attribute a ON a.attrelid=d.refobjid AND "
    "a.attnum=d.refobjsubid WHERE n.nspname='public' ORDER BY "
    "c.relname",
}
