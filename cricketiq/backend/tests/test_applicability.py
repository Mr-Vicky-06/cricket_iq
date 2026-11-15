"""Comprehensive tests for Deterministic Applicability Engine in CricketIQ."""

import pytest
from datetime import date
from typing import List, Optional

from cricketiq.backend.app.database.models import (
    MatchContext, CricketFormat, GenderCategory, DocumentAuthority,
    DocumentType, ScopeLevel, ApplicabilityBasis, DocumentStatus,
    SourceDocument, DocumentRelationship, RelationshipType
)
from cricketiq.backend.app.core.applicability_engine import ApplicabilityEngine
from cricketiq.backend.app.database.repository import RuleCatalog


class MockRuleCatalog:
    """Mock catalog providing verified test source documents and relationships."""

    def __init__(self, documents: List[SourceDocument], relationships: Optional[List[DocumentRelationship]] = None):
        self._docs = {d.id: d for d in documents}
        self._relationships = relationships or []

    def get_document(self, doc_id: str) -> Optional[SourceDocument]:
        return self._docs.get(doc_id)

    def list_active_documents(self) -> List[SourceDocument]:
        return [d for d in self._docs.values() if d.status == DocumentStatus.ACTIVE]

    def get_relationships(self, doc_id: str) -> List[DocumentRelationship]:
        return [r for r in self._relationships if r.source_doc_id == doc_id or r.target_doc_id == doc_id]

    def get_clause(self, clause_id: str):
        return None

    def get_clauses_for_document(self, doc_id: str):
        return []


@pytest.fixture
def test_catalog() -> MockRuleCatalog:
    # 1. ICC Men's T20I Playing Conditions (October 2026 Edition)
    icc_t20i_men_2026 = SourceDocument(
        id="ICC_T20I_MEN_2026",
        publisher=DocumentAuthority.ICC,
        title="ICC Men's Twenty20 International Playing Conditions",
        document_type=DocumentType.PLAYING_CONDITIONS,
        scope_level=ScopeLevel.FORMAT_PC,
        format=CricketFormat.T20I,
        category=GenderCategory.MENS,
        edition="October 2026",
        effective_from="2026-10-01",
        applicability_basis=ApplicabilityBasis.SERIES_START_DATE,
        official_url="https://www.icc-cricket.com/about/cricket/rules-and-regulations/playing-conditions",
        sha256="a" * 64,
        status=DocumentStatus.ACTIVE
    )

    # 2. ICC Men's T20I Playing Conditions (October 2024 Predecessor Edition)
    icc_t20i_men_2024 = SourceDocument(
        id="ICC_T20I_MEN_2024",
        publisher=DocumentAuthority.ICC,
        title="ICC Men's Twenty20 International Playing Conditions",
        document_type=DocumentType.PLAYING_CONDITIONS,
        scope_level=ScopeLevel.FORMAT_PC,
        format=CricketFormat.T20I,
        category=GenderCategory.MENS,
        edition="October 2024",
        effective_from="2024-10-01",
        effective_until="2026-09-30",
        applicability_basis=ApplicabilityBasis.SERIES_START_DATE,
        official_url="https://www.icc-cricket.com/about/cricket/rules-and-regulations/playing-conditions",
        sha256="b" * 64,
        status=DocumentStatus.ACTIVE
    )

    # 3. ICC Women's T20I Playing Conditions (October 2026 Edition)
    icc_t20i_women_2026 = SourceDocument(
        id="ICC_T20I_WOMEN_2026",
        publisher=DocumentAuthority.ICC,
        title="ICC Women's Twenty20 International Playing Conditions",
        document_type=DocumentType.PLAYING_CONDITIONS,
        scope_level=ScopeLevel.FORMAT_PC,
        format=CricketFormat.T20I,
        category=GenderCategory.WOMENS,
        edition="October 2026",
        effective_from="2026-10-01",
        applicability_basis=ApplicabilityBasis.SERIES_START_DATE,
        official_url="https://www.icc-cricket.com/about/cricket/rules-and-regulations/playing-conditions",
        sha256="c" * 64,
        status=DocumentStatus.ACTIVE
    )

    # 4. ICC Men's Test Playing Conditions (October 2026 Edition)
    icc_test_men_2026 = SourceDocument(
        id="ICC_TEST_MEN_2026",
        publisher=DocumentAuthority.ICC,
        title="ICC Men's Test Playing Conditions",
        document_type=DocumentType.PLAYING_CONDITIONS,
        scope_level=ScopeLevel.FORMAT_PC,
        format=CricketFormat.TEST,
        category=GenderCategory.MENS,
        edition="October 2026",
        effective_from="2026-10-01",
        applicability_basis=ApplicabilityBasis.SERIES_START_DATE,
        official_url="https://www.icc-cricket.com/about/cricket/rules-and-regulations/playing-conditions",
        sha256="d" * 64,
        status=DocumentStatus.ACTIVE
    )

    # 5. Competition: ICC Men's T20 World Cup 2026
    icc_t20_wc_2026 = SourceDocument(
        id="ICC_T20_WORLD_CUP_2026",
        publisher=DocumentAuthority.ICC,
        title="ICC Men's T20 World Cup 2026 Playing Conditions",
        document_type=DocumentType.COMPETITION_REGULATIONS,
        scope_level=ScopeLevel.COMPETITION_PC,
        format=CricketFormat.T20I,
        category=GenderCategory.MENS,
        competition="T20_WORLD_CUP_2026",
        edition="February 2026",
        effective_from="2026-02-01",
        effective_until="2026-03-31",
        applicability_basis=ApplicabilityBasis.COMPETITION_START_DATE,
        official_url="https://www.icc-cricket.com/about/cricket/rules-and-regulations/playing-conditions",
        sha256="e" * 64,
        status=DocumentStatus.ACTIVE
    )

    # 6. MCC Laws of Cricket (2017 Code 4th Edition 2026)
    mcc_laws_2026 = SourceDocument(
        id="MCC_LAWS_2026",
        publisher=DocumentAuthority.MCC,
        title="The Laws of Cricket (2017 Code 4th Edition - 2026)",
        document_type=DocumentType.LAW,
        scope_level=ScopeLevel.LAWS_BASELINE,
        edition="2026 Edition (4th Edition)",
        effective_from="2026-10-01",
        applicability_basis=ApplicabilityBasis.SEASON_EDITION,
        official_url="https://www.lords.org/mcc/the-laws-of-cricket",
        sha256="f" * 64,
        status=DocumentStatus.ACTIVE
    )

    # 7. MCC Laws of Cricket (2017 Code 3rd Edition 2022)
    mcc_laws_2022 = SourceDocument(
        id="MCC_LAWS_2022",
        publisher=DocumentAuthority.MCC,
        title="The Laws of Cricket (2017 Code 3rd Edition - 2022)",
        document_type=DocumentType.LAW,
        scope_level=ScopeLevel.LAWS_BASELINE,
        edition="2022 Edition (3rd Edition)",
        effective_from="2022-10-01",
        effective_until="2026-09-30",
        applicability_basis=ApplicabilityBasis.SEASON_EDITION,
        official_url="https://www.lords.org/mcc/the-laws-of-cricket",
        sha256="g" * 64,
        status=DocumentStatus.ACTIVE
    )

    relationships = [
        DocumentRelationship(
            id="REL_ICC_T20I_MODIFIES_MCC",
            source_doc_id="ICC_T20I_MEN_2026",
            target_doc_id="MCC_LAWS_2026",
            relationship_type=RelationshipType.MODIFIES,
            description="ICC Men's T20I Playing Conditions Clause 21.18 modifies MCC Law 21 by granting Free Hit on No balls.",
            supporting_clause_id="21.18"
        ),
        DocumentRelationship(
            id="REL_T20_WC_MODIFIES_T20I",
            source_doc_id="ICC_T20_WORLD_CUP_2026",
            target_doc_id="ICC_T20I_MEN_2026",
            relationship_type=RelationshipType.MODIFIES,
            description="T20 World Cup specific playing conditions overlay standard T20I playing conditions."
        )
    ]

    docs = [
        icc_t20i_men_2026, icc_t20i_men_2024, icc_t20i_women_2026,
        icc_test_men_2026, icc_t20_wc_2026, mcc_laws_2026, mcc_laws_2022
    ]
    return MockRuleCatalog(docs, relationships)


# --- Gate 6.1: ICC Transition Regression Tests ---

def test_icc_transition_series_started_sep_match_sep(test_catalog):
    """Series started 25 Sep 2026, match 28 Sep 2026 -> previous edition."""
    engine = ApplicabilityEngine()
    context = MatchContext(
        format=CricketFormat.T20I,
        category=GenderCategory.MENS,
        series_start_date="2026-09-25",
        match_date="2026-09-28"
    )
    decision = engine.resolve(context, test_catalog)

    assert not decision.is_ambiguous
    assert decision.primary_document is not None
    assert decision.primary_document.id == "ICC_T20I_MEN_2024"
    assert decision.baseline_document.id == "MCC_LAWS_2022"
    assert "SERIES_START_PRE_OCT_2026_APPLIES_PREVIOUS_EDITION" in decision.reason_codes


def test_icc_transition_ongoing_series_crossing_october_1(test_catalog):
    """Critical regression: Series started 25 Sep 2026, match 3 Oct 2026 -> previous edition (ongoing series!)."""
    engine = ApplicabilityEngine()
    context = MatchContext(
        format=CricketFormat.T20I,
        category=GenderCategory.MENS,
        series_start_date="2026-09-25",
        match_date="2026-10-03"
    )
    decision = engine.resolve(context, test_catalog)

    assert not decision.is_ambiguous
    assert decision.primary_document is not None
    assert decision.primary_document.id == "ICC_T20I_MEN_2024"  # Must remain previous edition!
    assert decision.baseline_document.id == "MCC_LAWS_2022"
    assert "SERIES_START_PRE_OCT_2026_APPLIES_PREVIOUS_EDITION" in decision.reason_codes


def test_icc_transition_series_started_oct_2(test_catalog):
    """Series started 2 Oct 2026, match 3 Oct 2026 -> October 2026 edition."""
    engine = ApplicabilityEngine()
    context = MatchContext(
        format=CricketFormat.T20I,
        category=GenderCategory.MENS,
        series_start_date="2026-10-02",
        match_date="2026-10-03"
    )
    decision = engine.resolve(context, test_catalog)

    assert not decision.is_ambiguous
    assert decision.primary_document.id == "ICC_T20I_MEN_2026"
    assert decision.baseline_document.id == "MCC_LAWS_2026"
    assert "SERIES_START_POST_OCT_2026_APPLIES_2026_EDITION" in decision.reason_codes


def test_icc_transition_series_started_boundary_day(test_catalog):
    """Series started 1 Oct 2026, match 1 Oct 2026 -> October 2026 edition."""
    engine = ApplicabilityEngine()
    context = MatchContext(
        format=CricketFormat.T20I,
        category=GenderCategory.MENS,
        series_start_date="2026-10-01",
        match_date="2026-10-01"
    )
    decision = engine.resolve(context, test_catalog)

    assert not decision.is_ambiguous
    assert decision.primary_document.id == "ICC_T20I_MEN_2026"
    assert decision.baseline_document.id == "MCC_LAWS_2026"


def test_missing_series_start_date_on_transition_boundary(test_catalog):
    """Match date 2026-10-03 with missing series_start_date must return unresolved/clarification."""
    engine = ApplicabilityEngine()
    context = MatchContext(
        format=CricketFormat.T20I,
        category=GenderCategory.MENS,
        series_start_date=None,
        match_date="2026-10-03"
    )
    decision = engine.resolve(context, test_catalog)

    assert decision.is_ambiguous
    assert "series_start_date" in decision.unresolved_conditions
    assert "REQUIRES_SERIES_START_DATE_CONFIRMATION" in decision.reason_codes
    assert "Please provide the series start date" in decision.clarification_needed


# --- Gate 6.2: Scope, Category, and Format Tests ---

def test_scope_mens_vs_womens_t20i(test_catalog):
    engine = ApplicabilityEngine()

    # Men's
    dec_men = engine.resolve(
        MatchContext(format=CricketFormat.T20I, category=GenderCategory.MENS, series_start_date="2026-10-05"),
        test_catalog
    )
    assert dec_men.primary_document.id == "ICC_T20I_MEN_2026"

    # Women's
    dec_women = engine.resolve(
        MatchContext(format=CricketFormat.T20I, category=GenderCategory.WOMENS, series_start_date="2026-10-05"),
        test_catalog
    )
    assert dec_women.primary_document.id == "ICC_T20I_WOMEN_2026"


def test_format_isolation_test_does_not_select_t20i(test_catalog):
    engine = ApplicabilityEngine()
    context = MatchContext(
        format=CricketFormat.TEST,
        category=GenderCategory.MENS,
        series_start_date="2026-10-05"
    )
    decision = engine.resolve(context, test_catalog)

    assert decision.primary_document.id == "ICC_TEST_MEN_2026"
    bundle_ids = [d.id for d in decision.selected_bundle]
    assert "ICC_T20I_MEN_2026" not in bundle_ids


def test_competition_specific_overlay_precedence(test_catalog):
    engine = ApplicabilityEngine()
    context = MatchContext(
        format=CricketFormat.T20I,
        category=GenderCategory.MENS,
        competition="T20_WORLD_CUP_2026",
        series_start_date="2026-02-15"
    )
    decision = engine.resolve(context, test_catalog)

    assert not decision.is_ambiguous
    assert decision.selected_bundle[0].id == "ICC_T20_WORLD_CUP_2026"
    assert decision.primary_document.id == "ICC_T20_WORLD_CUP_2026"
    # Precedence ranking: Competition PC -> Format PC -> MCC Laws
    bundle_ids = [d.id for d in decision.selected_bundle]
    assert bundle_ids == ["ICC_T20_WORLD_CUP_2026", "ICC_T20I_MEN_2024", "MCC_LAWS_2022"]


def test_domestic_league_rejected_safely(test_catalog):
    engine = ApplicabilityEngine()
    context = MatchContext(
        raw_query="Can a bowler bowl 5 overs in IPL?"
    )
    decision = engine.resolve(context, test_catalog)

    assert decision.is_ambiguous
    assert "DOMESTIC_REGULATION_OUT_OF_SCOPE" in decision.reason_codes
    assert "IPL" in decision.clarification_needed


def test_source_bundle_preserves_relationships(test_catalog):
    engine = ApplicabilityEngine()
    context = MatchContext(
        format=CricketFormat.T20I,
        category=GenderCategory.MENS,
        series_start_date="2026-10-05"
    )
    decision = engine.resolve(context, test_catalog)

    applied_rel_types = [r.relationship_type for r in decision.relationships_applied]
    assert RelationshipType.MODIFIES in applied_rel_types
    assert any("21.18" in (r.supporting_clause_id or "") for r in decision.relationships_applied)
