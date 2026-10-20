# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Frozen E1 PostgreSQL lifecycle guards, compiled offline but not server-tested.

Trigger functions use invoker rights and qualified relations. Ordinary writers
cannot delete retained principals/history or mutate the staged governance graph.
The database owner remains trusted; triggers are not an owner/superuser sandbox.
"""

from typing import TypeAlias

TriggerDefinition: TypeAlias = tuple[str, str, str]

FUNCTION_SIGNATURES: tuple[str, ...] = (
    "tenant_e1_retain_record()",
    "tenant_e1_identity_guard()",
    "tenant_e1_organization_guard()",
    "tenant_e1_membership_guard()",
    "tenant_e1_identity_companies()",
    "tenant_e1_assert_owner(integer)",
    "tenant_e1_owner_deferred()",
    "tenant_e1_assignment_guard()",
    "tenant_e1_closed_policy()",
)

FUNCTION_DEFINITIONS: tuple[str, ...] = (
    """CREATE FUNCTION public.tenant_e1_retain_record() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $e1$
BEGIN
    RAISE EXCEPTION 'E1 retained record cannot be removed or rewritten'
        USING ERRCODE = '23514', CONSTRAINT = 'ck_e1_retained_record';
END;
$e1$""",
    """CREATE FUNCTION public.tenant_e1_identity_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $e1$
BEGIN
    IF ROW(NEW.id, NEW.issuer, NEW.subject, NEW.created_at)
        IS DISTINCT FROM ROW(OLD.id, OLD.issuer, OLD.subject, OLD.created_at) THEN
        RAISE EXCEPTION 'identity keys are immutable'
            USING ERRCODE = '23514', CONSTRAINT = 'ck_e1_identity_immutable';
    END IF;
    IF NEW.revision <> OLD.revision + 1 THEN
        RAISE EXCEPTION 'identity revision must advance exactly once'
            USING ERRCODE = '23514', CONSTRAINT = 'ck_e1_identity_revision';
    END IF;
    IF OLD.status = 'retired' AND NEW.status <> 'retired' THEN
        RAISE EXCEPTION 'retired identity cannot be reactivated'
            USING ERRCODE = '23514', CONSTRAINT = 'ck_e1_identity_terminal';
    END IF;
    RETURN NEW;
END;
$e1$""",
    """CREATE FUNCTION public.tenant_e1_organization_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $e1$
BEGIN
    IF ROW(NEW.id, NEW.created_at) IS DISTINCT FROM ROW(OLD.id, OLD.created_at)
        OR (OLD.tenant_enforced_at IS NOT NULL
            AND NEW.tenant_enforced_at IS DISTINCT FROM OLD.tenant_enforced_at) THEN
        RAISE EXCEPTION 'company identity and enforcement marker are immutable'
            USING ERRCODE = '23514', CONSTRAINT = 'ck_e1_organization_immutable';
    END IF;
    IF NEW.revision <> OLD.revision + 1 THEN
        RAISE EXCEPTION 'company revision must advance exactly once'
            USING ERRCODE = '23514', CONSTRAINT = 'ck_e1_organization_revision';
    END IF;
    IF OLD.status = 'archived' AND NEW.status <> 'archived' THEN
        RAISE EXCEPTION 'archived company cannot be reactivated'
            USING ERRCODE = '23514', CONSTRAINT = 'ck_e1_organization_terminal';
    END IF;
    RETURN NEW;
END;
$e1$""",
    """CREATE FUNCTION public.tenant_e1_membership_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $e1$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        IF ROW(NEW.id, NEW.organization_id, NEW.identity_id, NEW.created_at)
            IS DISTINCT FROM ROW(OLD.id, OLD.organization_id, OLD.identity_id, OLD.created_at) THEN
            RAISE EXCEPTION 'membership endpoints are immutable'
                USING ERRCODE = '23514', CONSTRAINT = 'ck_e1_membership_immutable';
        END IF;
        IF NEW.revision <> OLD.revision + 1 THEN
            RAISE EXCEPTION 'membership revision must advance exactly once'
                USING ERRCODE = '23514', CONSTRAINT = 'ck_e1_membership_revision';
        END IF;
        IF OLD.status = 'revoked' AND NEW.status <> 'revoked' THEN
            IF NEW.status <> 'pending'
                OR NEW.enrollment_generation <> OLD.enrollment_generation + 1
                OR NEW.access_mode <> 'explicit-grants'
                OR NEW.accepted_at IS NOT NULL OR NEW.activated_at IS NOT NULL
                OR NEW.suspended_at IS NOT NULL OR NEW.revoked_at IS NOT NULL
                OR EXISTS (SELECT 1 FROM public.membership_restaurant_grants
                    WHERE membership_id = OLD.id) THEN
                RAISE EXCEPTION 're-enrollment requires a fresh empty pending generation'
                    USING ERRCODE = '23514', CONSTRAINT = 'ck_e1_membership_enrollment';
            END IF;
        ELSIF NEW.enrollment_generation <> OLD.enrollment_generation THEN
            RAISE EXCEPTION 'enrollment generation is immutable outside re-enrollment'
                USING ERRCODE = '23514', CONSTRAINT = 'ck_e1_membership_generation';
        END IF;
    END IF;
    -- A real company-row write serializes competing owner reductions. Merely
    -- locking that row at deferred-check time is insufficient under snapshot isolation.
    -- Writing the identity, rather than only sharing its lock, also serializes
    -- status changes against memberships invisible to an older RR snapshot.
    -- REPEATABLE READ / SERIALIZABLE writers must retry on 40001. Contexts must
    -- be resolved again after this deliberately conservative revision advance.
    UPDATE public.identities SET revision = revision + 1, updated_at = now()
        WHERE id = NEW.identity_id;
    UPDATE public.organizations SET revision = revision + 1, updated_at = now()
        WHERE id = NEW.organization_id;
    RETURN NEW;
END;
$e1$""",
    """CREATE FUNCTION public.tenant_e1_identity_companies() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $e1$
DECLARE company_id integer;
BEGIN
    IF NEW.status IS DISTINCT FROM OLD.status THEN
        FOR company_id IN SELECT DISTINCT organization_id
            FROM public.organization_memberships WHERE identity_id = NEW.id
            ORDER BY organization_id
        LOOP
            UPDATE public.organizations SET revision = revision + 1, updated_at = now()
                WHERE id = company_id;
        END LOOP;
    END IF;
    RETURN NULL;
END;
$e1$""",
    """CREATE FUNCTION public.tenant_e1_assert_owner(company_id integer) RETURNS void
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $e1$
DECLARE company_state text;
BEGIN
    SELECT status INTO company_state FROM public.organizations
        WHERE id = company_id FOR UPDATE;
    -- Separate statement: at READ COMMITTED this obtains a fresh snapshot after
    -- serialization. The earlier revision write forces a conflict at higher levels.
    IF company_state = 'active' AND NOT EXISTS (
        SELECT 1 FROM public.organization_memberships AS m
        JOIN public.identities AS i ON i.id = m.identity_id
        WHERE m.organization_id = company_id AND m.role_code = 'owner'
          AND m.status = 'active' AND m.access_mode = 'company-wide'
          AND m.accepted_at IS NOT NULL AND m.activated_at IS NOT NULL
          AND i.status = 'active'
    ) THEN
        RAISE EXCEPTION 'active company requires a qualifying active owner'
            USING ERRCODE = '23514', CONSTRAINT = 'ck_organization_active_owner';
    END IF;
END;
$e1$""",
    """CREATE FUNCTION public.tenant_e1_owner_deferred() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $e1$
BEGIN
    IF TG_TABLE_NAME = 'organizations' THEN
        PERFORM public.tenant_e1_assert_owner(NEW.id);
    ELSE
        PERFORM public.tenant_e1_assert_owner(NEW.organization_id);
    END IF;
    RETURN NULL;
END;
$e1$""",
    """CREATE FUNCTION public.tenant_e1_assignment_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $e1$
DECLARE old_key integer; new_key integer; company_state text; enforcement timestamptz;
BEGIN
    IF TG_TABLE_NAME IN ('owners', 'admins') THEN
        IF TG_OP <> 'INSERT' THEN old_key := OLD.identity_id; END IF;
        IF TG_OP <> 'DELETE' THEN new_key := NEW.identity_id; END IF;
    ELSE
        IF TG_OP <> 'INSERT' THEN old_key := OLD.organization_id; END IF;
        IF TG_OP <> 'DELETE' THEN new_key := NEW.organization_id; END IF;
    END IF;
    -- Untagged legacy rows retain their existing behavior throughout expansion.
    IF old_key IS NOT NULL THEN
        IF TG_OP = 'DELETE' THEN
            RAISE EXCEPTION 'linked resource must retain its historical identity'
                USING ERRCODE = '23514', CONSTRAINT = 'ck_e1_assignment_retained';
        END IF;
        IF new_key IS DISTINCT FROM old_key OR NEW.id IS DISTINCT FROM OLD.id THEN
            RAISE EXCEPTION 'resource assignment is immutable'
                USING ERRCODE = '23514', CONSTRAINT = 'ck_e1_assignment_immutable';
        END IF;
        IF TG_TABLE_NAME = 'restaurant_branches' THEN
            IF ROW(NEW.group_id, NEW.restaurant_id)
                IS DISTINCT FROM ROW(OLD.group_id, OLD.restaurant_id) THEN
                RAISE EXCEPTION 'linked group endpoints are immutable'
                    USING ERRCODE = '23514', CONSTRAINT = 'ck_e1_group_link_immutable';
            END IF;
        END IF;
    ELSIF new_key IS NOT NULL AND TG_TABLE_NAME NOT IN ('owners', 'admins') THEN
        SELECT status, tenant_enforced_at INTO company_state, enforcement
            FROM public.organizations WHERE id = new_key FOR SHARE;
        IF company_state IS DISTINCT FROM 'draft' OR enforcement IS NOT NULL THEN
            RAISE EXCEPTION 'E1 assignment requires a draft unenforced company'
                USING ERRCODE = '23514', CONSTRAINT = 'ck_e1_assignment_staged';
        END IF;
    END IF;
    IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
    RETURN NEW;
END;
$e1$""",
    """CREATE FUNCTION public.tenant_e1_closed_policy() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $e1$
BEGIN
    -- E1 does not release acceptance/sealing or tenant-facing policy editing.
    -- A separately reviewed revision must replace this fence with the complete
    -- immutable proposal-graph and accepted-governance contract before use.
    RAISE EXCEPTION 'E1 governance and policy mutation are closed pending separate review'
        USING ERRCODE = '23514', CONSTRAINT = 'ck_e1_governance_closed';
END;
$e1$""",
)

TRIGGER_DEFINITIONS: tuple[TriggerDefinition, ...] = (
    (
        "identities",
        "tr_e1_identity_guard",
        (
            "CREATE TRIGGER tr_e1_identity_guard BEFORE UPDATE ON public.identities "
            "FOR EACH ROW EXECUTE FUNCTION public.tenant_e1_identity_guard()"
        ),
    ),
    (
        "identities",
        "tr_e1_identity_companies",
        (
            "CREATE TRIGGER tr_e1_identity_companies AFTER UPDATE ON public.identities "
            "FOR EACH ROW EXECUTE FUNCTION public.tenant_e1_identity_companies()"
        ),
    ),
    (
        "organizations",
        "tr_e1_organization_guard",
        (
            "CREATE TRIGGER tr_e1_organization_guard BEFORE UPDATE ON public.organizations "
            "FOR EACH ROW EXECUTE FUNCTION public.tenant_e1_organization_guard()"
        ),
    ),
    (
        "organization_memberships",
        "tr_e1_membership_guard",
        (
            "CREATE TRIGGER tr_e1_membership_guard BEFORE INSERT OR UPDATE "
            "ON public.organization_memberships FOR EACH ROW "
            "EXECUTE FUNCTION public.tenant_e1_membership_guard()"
        ),
    ),
    *tuple(
        (
            table,
            name,
            (
                f"CREATE CONSTRAINT TRIGGER {name} AFTER INSERT OR UPDATE ON public.{table} "
                "DEFERRABLE INITIALLY DEFERRED FOR EACH ROW "
                "EXECUTE FUNCTION public.tenant_e1_owner_deferred()"
            ),
        )
        for table, name in (
            ("organizations", "ct_e1_organization_owner"),
            ("organization_memberships", "ct_e1_membership_owner"),
        )
    ),
    *tuple(
        (
            table,
            f"tr_e1_{table}_retain",
            (
                f"CREATE TRIGGER tr_e1_{table}_retain BEFORE DELETE ON public.{table} "
                "FOR EACH ROW EXECUTE FUNCTION public.tenant_e1_retain_record()"
            ),
        )
        for table in ("identities", "organizations", "organization_memberships")
    ),
    (
        "tenant_audit_events",
        "tr_e1_audit_retain",
        (
            "CREATE TRIGGER tr_e1_audit_retain BEFORE UPDATE OR DELETE ON public.tenant_audit_events "
            "FOR EACH ROW EXECUTE FUNCTION public.tenant_e1_retain_record()"
        ),
    ),
    *tuple(
        (
            table,
            f"tr_e1_{table}_truncate",
            (
                f"CREATE TRIGGER tr_e1_{table}_truncate BEFORE TRUNCATE ON public.{table} "
                "FOR EACH STATEMENT EXECUTE FUNCTION public.tenant_e1_retain_record()"
            ),
        )
        for table in (
            "identities",
            "organizations",
            "tenant_roles",
            "tenant_role_permissions",
            "organization_memberships",
            "membership_restaurant_grants",
            "membership_change_proposals",
            "membership_proposal_restaurants",
            "tenant_audit_events",
        )
    ),
    *tuple(
        (
            table,
            f"tr_e1_{table}_assignment",
            (
                f"CREATE TRIGGER tr_e1_{table}_assignment BEFORE INSERT OR UPDATE OR DELETE "
                f"ON public.{table} FOR EACH ROW EXECUTE FUNCTION public.tenant_e1_assignment_guard()"
            ),
        )
        for table in (
            "restaurants",
            "restaurant_groups",
            "restaurant_branches",
            "owners",
            "admins",
        )
    ),
    *tuple(
        (
            table,
            f"tr_e1_{table}_closed",
            (
                f"CREATE TRIGGER tr_e1_{table}_closed BEFORE INSERT OR UPDATE OR DELETE "
                f"ON public.{table} FOR EACH ROW EXECUTE FUNCTION public.tenant_e1_closed_policy()"
            ),
        )
        for table in (
            "tenant_roles",
            "tenant_role_permissions",
            "membership_change_proposals",
            "membership_proposal_restaurants",
        )
    ),
)
