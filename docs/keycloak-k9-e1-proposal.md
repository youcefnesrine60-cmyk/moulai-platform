# K9.2-B1 ? E1 migration proposal for review

Status: **review-only SQL; not an Alembic revision and never executed in B1**.

This proposal accompanies [B1 validation](keycloak-k9-b1-validation.md) and the
[approved detailed design](keycloak-k9-detailed-design.md). It creates no real
identity, company, membership, profile link or policy grant. PostgreSQL DDL
compilation is not PostgreSQL execution or a migration rehearsal.

## 1. Scope and prerequisites

The nine tenant tables use the existing declarative registry with separate
preparatory metadata. The `restaurants` and `admins` table declarations in that
metadata are external FK target contracts, not tables to create or replacements
for existing ORM mappings. They are excluded from the CREATE TABLE inventory.
`Restaurant.group_id`, current authentication, payments, platform RBAC and
application startup imports remain unchanged.

E1 needs an approved starting revision and a fresh read-only schema inventory.
Existing constraint names, index definitions, table ownership and privileges must
be compared before translating this proposal into a revision. No IF NOT EXISTS
or automatic conflict suppression should hide an incompatible schema. Keep all
existing resource IDs, owner IDs, financial values and group associations.

Do not call `TENANT_METADATA.create_all` on a deployed database: its reference
contracts are intentionally partial. Only local in-memory tests create these
reference tables. A reviewed Alembic revision must explicitly name its new
objects and approved existing-table additions.

## 2. Compiled foundation DDL and Restaurant expansion

The statements below are compiled from the B1 models using the PostgreSQL
dialect. No engine connection was used. The Restaurant ALTER statements are
explicit proposals, since its live ORM mapper deliberately has no new column.
Organization assignment stays nullable and unenforced during E1; there is no
backfill or company activation in this stage.

```sql
CREATE TABLE identities (
    issuer VARCHAR(1024) COLLATE "C" NOT NULL,
    subject VARCHAR(255) COLLATE "C" NOT NULL,
    status VARCHAR(16) DEFAULT 'suspended' NOT NULL,
    revision BIGINT DEFAULT '1' NOT NULL,
    id SERIAL NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_identities_issuer_subject UNIQUE (issuer, subject),
    CONSTRAINT ck_identity_status CHECK (status IN ('active','suspended','retired')),
    CONSTRAINT ck_identity_revision CHECK (revision > 0),
    CONSTRAINT ck_identity_issuer CHECK (length(issuer) BETWEEN 1 AND 1024 AND issuer = trim(issuer) AND issuer LIKE 'https://%%'),
    CONSTRAINT ck_identity_subject CHECK (length(subject) BETWEEN 1 AND 255 AND subject = trim(subject)),
    CONSTRAINT ck_identity_ascii CHECK (octet_length(issuer) = length(issuer) AND octet_length(subject) = length(subject) AND issuer !~ '[[:cntrl:]]' AND subject !~ '[[:cntrl:]]')
);


CREATE TABLE organizations (
    name VARCHAR(255) NOT NULL,
    status VARCHAR(16) DEFAULT 'draft' NOT NULL,
    revision BIGINT DEFAULT '1' NOT NULL,
    tenant_enforced_at TIMESTAMP WITH TIME ZONE,
    id SERIAL NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT ck_org_name CHECK (length(trim(name)) BETWEEN 1 AND 255 AND name = trim(name)),
    CONSTRAINT ck_org_status CHECK (status IN ('draft','active','suspended','archived')),
    CONSTRAINT ck_org_revision CHECK (revision > 0),
    CONSTRAINT ck_org_enforcement CHECK (status != 'active' OR tenant_enforced_at IS NOT NULL)
);


CREATE TABLE tenant_roles (
    code VARCHAR(16) NOT NULL,
    policy_revision BIGINT DEFAULT '1' NOT NULL,
    PRIMARY KEY (code),
    CONSTRAINT ck_tenant_role_code CHECK (code IN ('owner','manager','employee')),
    CONSTRAINT ck_tenant_role_revision CHECK (policy_revision > 0)
);


CREATE TABLE organization_memberships (
    organization_id INTEGER NOT NULL,
    identity_id INTEGER NOT NULL,
    role_code VARCHAR(16) NOT NULL,
    access_mode VARCHAR(20) DEFAULT 'explicit-grants' NOT NULL,
    status VARCHAR(16) DEFAULT 'pending' NOT NULL,
    revision BIGINT DEFAULT '1' NOT NULL,
    enrollment_generation BIGINT NOT NULL,
    accepted_at TIMESTAMP WITH TIME ZONE,
    activated_at TIMESTAMP WITH TIME ZONE,
    suspended_at TIMESTAMP WITH TIME ZONE,
    revoked_at TIMESTAMP WITH TIME ZONE,
    id SERIAL NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_membership_identity UNIQUE (organization_id, identity_id),
    CONSTRAINT uq_membership_mode UNIQUE (organization_id, id, access_mode),
    CONSTRAINT uq_membership_actor UNIQUE (organization_id, id, identity_id),
    CONSTRAINT ck_membership_status CHECK (status IN ('pending','active','suspended','revoked')),
    CONSTRAINT ck_membership_mode CHECK (access_mode IN ('company-wide','explicit-grants')),
    CONSTRAINT ck_membership_owner_scope CHECK (role_code != 'owner' OR access_mode = 'company-wide'),
    CONSTRAINT ck_membership_revision CHECK (revision > 0 AND enrollment_generation > 0),
    CONSTRAINT ck_membership_acceptance CHECK (status != 'active' OR (accepted_at IS NOT NULL AND activated_at IS NOT NULL)),
    CONSTRAINT ck_membership_suspension CHECK (status != 'suspended' OR suspended_at IS NOT NULL),
    CONSTRAINT ck_membership_revocation CHECK (status != 'revoked' OR revoked_at IS NOT NULL),
    CONSTRAINT ck_membership_pending CHECK (status != 'pending' OR (accepted_at IS NULL AND activated_at IS NULL)),
    FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE RESTRICT,
    FOREIGN KEY(identity_id) REFERENCES identities (id) ON DELETE RESTRICT,
    FOREIGN KEY(role_code) REFERENCES tenant_roles (code) ON DELETE RESTRICT
);

CREATE INDEX ix_membership_identity_state ON organization_memberships (identity_id, status, organization_id);
CREATE INDEX ix_membership_org_role ON organization_memberships (organization_id, status, role_code);
CREATE INDEX ix_membership_role ON organization_memberships (role_code);

ALTER TABLE restaurants ADD COLUMN organization_id INTEGER;
ALTER TABLE restaurants ADD CONSTRAINT fk_restaurants_org FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE RESTRICT NOT VALID;
ALTER TABLE restaurants ADD CONSTRAINT uq_restaurants_org_id UNIQUE (organization_id, id);
CREATE INDEX ix_restaurants_organization_id ON restaurants (organization_id);

CREATE TABLE tenant_role_permissions (
    role_code VARCHAR(16) NOT NULL,
    permission_code VARCHAR(80) NOT NULL,
    PRIMARY KEY (role_code, permission_code),
    CONSTRAINT ck_tenant_role_permission CHECK ((role_code = 'employee' AND permission_code IN ('tenant.branches.read', 'tenant.catalog.read', 'tenant.membership.self.leave', 'tenant.membership.self.read', 'tenant.orders.fulfill', 'tenant.orders.read', 'tenant.restaurants.read')) OR (role_code = 'manager' AND permission_code IN ('tenant.agents.manage', 'tenant.agents.read', 'tenant.branches.manage', 'tenant.branches.read', 'tenant.catalog.manage', 'tenant.catalog.read', 'tenant.conversations.read', 'tenant.conversations.respond', 'tenant.groups.read', 'tenant.membership.self.leave', 'tenant.membership.self.read', 'tenant.orders.fulfill', 'tenant.orders.manage', 'tenant.orders.read', 'tenant.organization.read', 'tenant.reports.read', 'tenant.restaurants.read', 'tenant.restaurants.update')) OR (role_code = 'owner' AND permission_code IN ('tenant.agents.manage', 'tenant.agents.read', 'tenant.billing.checkout', 'tenant.billing.read', 'tenant.branches.manage', 'tenant.branches.read', 'tenant.catalog.manage', 'tenant.catalog.read', 'tenant.conversations.read', 'tenant.conversations.respond', 'tenant.groups.manage', 'tenant.groups.read', 'tenant.membership.self.leave', 'tenant.membership.self.read', 'tenant.memberships.manage', 'tenant.memberships.read', 'tenant.orders.fulfill', 'tenant.orders.manage', 'tenant.orders.read', 'tenant.organization.read', 'tenant.organization.suspend', 'tenant.organization.update', 'tenant.ownership.manage', 'tenant.receipts.submit', 'tenant.reports.read', 'tenant.restaurants.read', 'tenant.restaurants.update'))),
    FOREIGN KEY(role_code) REFERENCES tenant_roles (code) ON DELETE RESTRICT
);


CREATE TABLE membership_change_proposals (
    organization_id INTEGER NOT NULL,
    target_membership_id INTEGER NOT NULL,
    target_identity_id INTEGER NOT NULL,
    actor_kind VARCHAR(16) NOT NULL,
    actor_membership_id INTEGER,
    actor_identity_id INTEGER,
    actor_admin_id INTEGER,
    proposed_role_code VARCHAR(16) NOT NULL,
    proposed_access_mode VARCHAR(20) NOT NULL,
    expected_actor_revision BIGINT,
    expected_target_revision BIGINT NOT NULL,
    enrollment_generation BIGINT NOT NULL,
    status VARCHAR(16) DEFAULT 'pending' NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    applied_at TIMESTAMP WITH TIME ZONE,
    id SERIAL NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_proposal_mode UNIQUE (organization_id, id, proposed_access_mode),
    CONSTRAINT ck_proposal_mode CHECK (proposed_access_mode IN ('company-wide','explicit-grants')),
    CONSTRAINT ck_proposal_owner_scope CHECK (proposed_role_code != 'owner' OR proposed_access_mode = 'company-wide'),
    CONSTRAINT ck_proposal_status CHECK (status IN ('pending','applied','cancelled','expired')),
    CONSTRAINT ck_proposal_revision CHECK (expected_target_revision > 0 AND enrollment_generation > 0),
    CONSTRAINT ck_proposal_actor CHECK ((actor_kind = 'tenant' AND actor_membership_id IS NOT NULL AND actor_identity_id IS NOT NULL AND actor_admin_id IS NULL AND expected_actor_revision IS NOT NULL AND expected_actor_revision > 0) OR (actor_kind = 'platform' AND actor_membership_id IS NULL AND actor_identity_id IS NULL AND actor_admin_id IS NOT NULL AND expected_actor_revision IS NULL)),
    CONSTRAINT ck_proposal_application CHECK ((status = 'applied' AND applied_at IS NOT NULL) OR (status != 'applied' AND applied_at IS NULL)),
    CONSTRAINT fk_proposal_target FOREIGN KEY(organization_id, target_membership_id, target_identity_id) REFERENCES organization_memberships (organization_id, id, identity_id) ON DELETE RESTRICT,
    CONSTRAINT fk_proposal_actor FOREIGN KEY(organization_id, actor_membership_id, actor_identity_id) REFERENCES organization_memberships (organization_id, id, identity_id) ON DELETE RESTRICT,
    FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE RESTRICT,
    FOREIGN KEY(actor_admin_id) REFERENCES admins (id) ON DELETE RESTRICT,
    FOREIGN KEY(proposed_role_code) REFERENCES tenant_roles (code) ON DELETE RESTRICT
);

CREATE INDEX ix_proposal_actor ON membership_change_proposals (organization_id, actor_membership_id, actor_identity_id);
CREATE INDEX ix_proposal_target ON membership_change_proposals (organization_id, target_membership_id, target_identity_id);

CREATE TABLE membership_restaurant_grants (
    organization_id INTEGER NOT NULL,
    membership_id INTEGER NOT NULL,
    restaurant_id INTEGER NOT NULL,
    access_mode VARCHAR(20) DEFAULT 'explicit-grants' NOT NULL,
    id SERIAL NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_membership_restaurant UNIQUE (membership_id, restaurant_id),
    CONSTRAINT ck_grant_mode CHECK (access_mode = 'explicit-grants'),
    CONSTRAINT fk_grant_membership FOREIGN KEY(organization_id, membership_id, access_mode) REFERENCES organization_memberships (organization_id, id, access_mode) ON DELETE RESTRICT,
    CONSTRAINT fk_grant_restaurant FOREIGN KEY(organization_id, restaurant_id) REFERENCES restaurants (organization_id, id) ON DELETE RESTRICT
);

CREATE INDEX ix_grant_membership ON membership_restaurant_grants (organization_id, membership_id, access_mode);
CREATE INDEX ix_grant_restaurant ON membership_restaurant_grants (organization_id, restaurant_id);

CREATE TABLE tenant_audit_events (
    organization_id INTEGER NOT NULL,
    actor_kind VARCHAR(16) NOT NULL,
    actor_membership_id INTEGER,
    actor_identity_id INTEGER,
    actor_admin_id INTEGER,
    target_membership_id INTEGER NOT NULL,
    target_identity_id INTEGER NOT NULL,
    action VARCHAR(64) NOT NULL,
    previous_revision BIGINT NOT NULL,
    resulting_revision BIGINT NOT NULL,
    enrollment_generation BIGINT NOT NULL,
    reason_code VARCHAR(64) NOT NULL,
    correlation_id VARCHAR(64) NOT NULL,
    policy_before JSON NOT NULL,
    policy_after JSON NOT NULL,
    id SERIAL NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT ck_audit_action CHECK (length(trim(action)) > 0),
    CONSTRAINT ck_audit_reason CHECK (length(trim(reason_code)) > 0 AND length(trim(correlation_id)) > 0),
    CONSTRAINT ck_audit_revisions CHECK (previous_revision > 0 AND resulting_revision > previous_revision AND enrollment_generation > 0),
    CONSTRAINT ck_audit_actor CHECK ((actor_kind = 'tenant' AND actor_membership_id IS NOT NULL AND actor_identity_id IS NOT NULL AND actor_admin_id IS NULL) OR (actor_kind = 'platform' AND actor_membership_id IS NULL AND actor_identity_id IS NULL AND actor_admin_id IS NOT NULL)),
    CONSTRAINT fk_audit_target FOREIGN KEY(organization_id, target_membership_id, target_identity_id) REFERENCES organization_memberships (organization_id, id, identity_id) ON DELETE RESTRICT,
    CONSTRAINT fk_audit_actor FOREIGN KEY(organization_id, actor_membership_id, actor_identity_id) REFERENCES organization_memberships (organization_id, id, identity_id) ON DELETE RESTRICT,
    FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE RESTRICT,
    FOREIGN KEY(actor_admin_id) REFERENCES admins (id) ON DELETE RESTRICT
);

CREATE INDEX ix_audit_actor ON tenant_audit_events (organization_id, actor_membership_id, actor_identity_id);
CREATE INDEX ix_audit_target ON tenant_audit_events (organization_id, target_membership_id, target_identity_id);

CREATE TABLE membership_proposal_restaurants (
    organization_id INTEGER NOT NULL,
    proposal_id INTEGER NOT NULL,
    restaurant_id INTEGER NOT NULL,
    proposed_access_mode VARCHAR(20) DEFAULT 'explicit-grants' NOT NULL,
    id SERIAL NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_proposal_restaurant UNIQUE (proposal_id, restaurant_id),
    CONSTRAINT ck_proposal_restaurant_mode CHECK (proposed_access_mode = 'explicit-grants'),
    CONSTRAINT fk_proposal_restaurant_intent FOREIGN KEY(organization_id, proposal_id, proposed_access_mode) REFERENCES membership_change_proposals (organization_id, id, proposed_access_mode) ON DELETE RESTRICT,
    CONSTRAINT fk_proposal_restaurant_resource FOREIGN KEY(organization_id, restaurant_id) REFERENCES restaurants (organization_id, id) ON DELETE RESTRICT
);

CREATE INDEX ix_proposal_restaurant ON membership_proposal_restaurants (organization_id, restaurant_id);
CREATE INDEX ix_proposal_restaurant_parent ON membership_proposal_restaurants (organization_id, proposal_id, proposed_access_mode);

```

Python/client defaults are visible in the ORM; server defaults in the compiled
DDL are explicit. New Identities default to suspended, companies to draft,
memberships/proposals to pending and restaurant scope to explicit grants.
No permission or identity lookup falls back to a seeded Python template.
Permission ceilings are validation constraints, not implicit grants. Fulfillment
is blocked by the B1 authorization layer for every role.

## 3. Additional expansion to review, without mapping or populating it

These nullable additions prepare the design's later grouping/profile phase;
they are not required to call existing routes, and B1 does not change their ORM
mappings. Decide their exact E1 inclusion before writing a revision.

```sql
ALTER TABLE restaurant_groups ADD COLUMN organization_id INTEGER;
ALTER TABLE restaurant_groups ADD CONSTRAINT fk_restaurant_groups_org
    FOREIGN KEY (organization_id) REFERENCES organizations(id)
    ON DELETE RESTRICT NOT VALID;
ALTER TABLE restaurant_groups ADD CONSTRAINT uq_restaurant_groups_org_id
    UNIQUE (organization_id, id);
CREATE INDEX ix_restaurant_groups_org ON restaurant_groups (organization_id);

ALTER TABLE restaurant_branches ADD COLUMN organization_id INTEGER;
ALTER TABLE restaurant_branches ADD CONSTRAINT fk_group_link_group_org
    FOREIGN KEY (organization_id, group_id)
    REFERENCES restaurant_groups(organization_id, id) ON DELETE RESTRICT NOT VALID;
ALTER TABLE restaurant_branches ADD CONSTRAINT fk_group_link_restaurant_org
    FOREIGN KEY (organization_id, restaurant_id)
    REFERENCES restaurants(organization_id, id) ON DELETE RESTRICT NOT VALID;
CREATE INDEX ix_group_link_org_group ON restaurant_branches (organization_id, group_id);
CREATE INDEX ix_group_link_org_restaurant ON restaurant_branches (organization_id, restaurant_id);

ALTER TABLE owners ADD COLUMN identity_id INTEGER;
ALTER TABLE owners ADD CONSTRAINT fk_owner_identity
    FOREIGN KEY (identity_id) REFERENCES identities(id) ON DELETE RESTRICT NOT VALID;
ALTER TABLE owners ADD CONSTRAINT uq_owner_identity UNIQUE (identity_id);
ALTER TABLE admins ADD COLUMN identity_id INTEGER;
ALTER TABLE admins ADD CONSTRAINT fk_admin_identity
    FOREIGN KEY (identity_id) REFERENCES identities(id) ON DELETE RESTRICT NOT VALID;
ALTER TABLE admins ADD CONSTRAINT uq_admin_identity UNIQUE (identity_id);
```

Do not add unique `(group_id, restaurant_id)` to existing links until duplicates
and references are reviewed. E1 does not union conflicting groups, populate
company/profile columns, drop `Restaurant.group_id`, enforce NOT NULL on old
resources or reinterpret legacy owner associations. The future unique-link
constraint belongs to validated reconciliation, not an assumption about live data.

## 4. Required database-level lifecycle enforcement

ORM update/delete events are implemented for immutable keys and audit history.
They cannot protect SQL bulk updates, database consoles or all proposal-child
mutations. The following review draft illustrates the mandatory PostgreSQL
last-owner constraint; it is not installed or claimed tested by B1.

```sql
CREATE FUNCTION tenant_assert_active_owner(company_id INTEGER) RETURNS VOID
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
DECLARE company_state TEXT;
BEGIN
    SELECT status INTO company_state FROM public.organizations
        WHERE id = company_id FOR UPDATE;
    IF company_state = 'active' AND NOT EXISTS (
        SELECT 1 FROM public.organization_memberships AS m
        JOIN public.identities AS i ON i.id = m.identity_id
        WHERE m.organization_id = company_id AND m.role_code = 'owner'
          AND m.status = 'active' AND m.access_mode = 'company-wide'
          AND m.accepted_at IS NOT NULL AND m.activated_at IS NOT NULL
          AND i.status = 'active'
    ) THEN
        RAISE EXCEPTION 'active company requires an active owner'
            USING ERRCODE = '23514', CONSTRAINT = 'ck_organization_active_owner';
    END IF;
END;
$$;

CREATE FUNCTION tenant_check_owner_deferred() RETURNS TRIGGER
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
DECLARE company_id INTEGER; identity_key INTEGER;
BEGIN
    IF TG_TABLE_NAME = 'organizations' THEN
        IF TG_OP = 'DELETE' THEN company_id := OLD.id;
        ELSE company_id := NEW.id; END IF;
        PERFORM public.tenant_assert_active_owner(company_id);
    ELSIF TG_TABLE_NAME = 'organization_memberships' THEN
        IF TG_OP = 'DELETE' THEN company_id := OLD.organization_id;
        ELSE company_id := NEW.organization_id; END IF;
        PERFORM public.tenant_assert_active_owner(company_id);
    ELSIF TG_TABLE_NAME = 'identities' THEN
        IF TG_OP = 'DELETE' THEN identity_key := OLD.id;
        ELSE identity_key := NEW.id; END IF;
        FOR company_id IN SELECT DISTINCT organization_id
            FROM public.organization_memberships WHERE identity_id = identity_key
            ORDER BY organization_id
        LOOP
            PERFORM public.tenant_assert_active_owner(company_id);
        END LOOP;
    END IF;
    RETURN NULL;
END;
$$;

CREATE CONSTRAINT TRIGGER ct_company_active_owner
AFTER INSERT OR UPDATE OR DELETE ON organizations
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
EXECUTE FUNCTION tenant_check_owner_deferred();
CREATE CONSTRAINT TRIGGER ct_membership_active_owner
AFTER INSERT OR UPDATE OR DELETE ON organization_memberships
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
EXECUTE FUNCTION tenant_check_owner_deferred();
CREATE CONSTRAINT TRIGGER ct_identity_active_owner
AFTER UPDATE OR DELETE ON identities
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
EXECUTE FUNCTION tenant_check_owner_deferred();
```

Before adoption, review and test the trigger with row locking and READ COMMITTED
snapshots, identity/company multi-row operations and bounded deadlock retries.
The old company of a moved membership must also be checked if such moves are
permitted; the approved design instead forbids changing membership endpoints.
Database immutability guards must enforce that prohibition before owner checks
are relied upon. B1 exposes no owner mutation or company activation service.

The executable revision must also implement and test the following guards,
not substitute ORM-only assertions:

| Guard | Required SQL-level rule |
| --- | --- |
| Identity | Immutable id/issuer/subject; retained lifecycle rather than ordinary DELETE. |
| Company | Immutable ID and non-null enforcement marker; ordinary DELETE prohibited. |
| Membership | Immutable ID/company/identity; ordinary DELETE prohibited; revision-qualified writes. |
| Restaurant/group assignment | Reviewed initial NULL-to-company assignment only; no ordinary company reassignment. |
| Audit | Ordinary runtime role may insert/read required events, never UPDATE/DELETE; schema owner remains separately trusted. |
| Proposal | Immutable intent and restaurant set after sealing; only valid state transitions; target acceptance and actor authority checked by a reviewed service. |
| Role policy | No tenant-facing mutation; locked reviewed provisioning increments policy_revision. |

Proposal sealing/acceptance, owner transfer and emergency recovery are not B1
operations. Their complete SQL lifecycle guards and service implementations must
be reviewed before those operations become possible. The compiled proposal
schema alone is not acceptance/provisioning authority.

## 5. Role policy provisioning and integrity verification

No live seed runs in B1. If separately approved for B2, provision only the three
tenant role rows and the reviewed section-3 permission assignments, omitting
`tenant.orders.fulfill` for all roles until its transition review. Do not insert
identities, companies, memberships, profile links or grants. Do not alter global
roles, permissions, role_permissions or existing administrator assignments.

Before migration, review duplicate constraint names and IDs and generate the
actual plan against the attested test schema. After migration, compare existing
business tables, row counts, foreign keys, financial amounts and platform grants
before/after. Test new constraints with transaction-scoped synthetic records and
rollback; do not enable real organizations or reset existing test data.

FK/CHECK constraints added NOT VALID require later validation after reviewed
backfill. Unique constraints cannot be treated as NOT VALID. Index concurrency,
lock duration and Alembic transaction boundaries require actual PostgreSQL
rehearsal. No migration success or lock/concurrency guarantee is asserted here.

## 6. B2 authorization gate and rollback

B2 requires separate approval for revision creation and for its precise isolated
execution target. Mandatory preflight must attest development project/branch,
endpoint and actual `neondb_test`, excluding the protected production endpoint.
Any missing evidence refuses writes; production DATABASE_URL is never a fallback.

Create the revision only after that scope is approved. Verify upgrade and
rollback on a separately approved isolated target with backup/recovery evidence.
Prefer leaving unused additive structures over dropping populated history.
No company cutover, identity linking, group reconciliation, business-route
conversion, production migration or deployment is included in E1 authorization.
