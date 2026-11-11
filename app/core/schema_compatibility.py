# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# EXPLICIT HISTORICAL SCHEMA READ BOUNDARIES
# Relate versioned additive features to exact installed revisions, independently of imported models.
# ==============================================

"""No environment switch or unknown revision can waive current schema requirements."""

# isort: split
# ==============================================
# IMMUTABLE CONTRACT DEPENDENCY
# Use a frozen value object so a selected read contract cannot be changed in place.
# ==============================================

from dataclasses import dataclass

# ==============================================
# REVIEWED ADDITIVE HISTORY
# These names originate in the O3, O4 and O5 migrations; no schema is inferred from ORM imports.
# ==============================================

HISTORICAL_STAGES = {
    "dce91870b4a2": 0,
    "e1a92b200001": 0,
    "e1b92b200001": 0,
    "s1a20261028": 0,
    "s1b20261028": 0,
    "d1a20261102": 0,
    "d1b20261103": 0,
    "d1c20261104": 0,
    "d1d20261105": 0,
    "o120261108": 1,
    "o220261108": 2,
    "o320261108": 3,
    "o420261108": 4,
    "o520261111": 5,
}
ADDITIVE_TABLE_STAGES = {
    "subscription_base_prices": 3,
    "billing_country_profiles": 4,
    "billing_country_evidence": 4,
    "billing_country_requests": 4,
    "billing_country_decisions": 4,
    "enrollment_documents": 4,
    "enrollment_dossiers": 4,
    "enrollment_document_events": 4,
    "subscription_documents": 5,
    "subscription_document_events": 5,
}

# ==============================================
# IMMUTABLE REQUIRED-SCHEMA CONTRACT
# Omissions apply only to later additive tables; shared columns and ownership protections remain required.
# ==============================================


@dataclass(frozen=True)
class HistoricalSchemaCompatibility:
    """Describe later absent tables and whether retained O1 actors must already exist."""

    tables_not_yet_introduced: frozenset[str]
    retained_actor_required: bool


# ==============================================
# EXACT INSTALLED REVISION SELECTION
# Unknown, empty or mixed histories receive every current requirement, never a permissive fallback.
# ==============================================


def historical_schema_compatibility(
    *, revisions: frozenset[str]
) -> HistoricalSchemaCompatibility:
    """Use a single reviewed revision or the explicitly reviewed dual-head S1b history.

    This compatibility does not activate newer features. Their own admission
    checks and database operations still require their actual migrations.
    """
    stage = None
    if len(revisions) == 1:
        stage = HISTORICAL_STAGES.get(next(iter(revisions)))
    elif revisions == {"e1b92b200001", "s1b20261028"}:
        stage = 0
    return HistoricalSchemaCompatibility(
        tables_not_yet_introduced=frozenset(
            name
            for name, introduced in ADDITIVE_TABLE_STAGES.items()
            if stage is not None and stage < introduced
        ),
        retained_actor_required=stage is None or stage >= 1,
    )
