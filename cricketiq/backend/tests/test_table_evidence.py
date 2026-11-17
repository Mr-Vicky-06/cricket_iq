"""Unit tests for Structured Table Evidence Hydration (Phase 6 Gate 3 Task 3.4).
"""

import pytest
import hashlib
from cricketiq.backend.app.retrieval.tables.table_service import (
    TableEvidence,
    TableValidationStatus,
    TableEvidenceService
)


@pytest.fixture
def table_service():
    """Create service instance with auto_load=False for controlled unit testing."""
    return TableEvidenceService(auto_load=False)


@pytest.fixture
def sample_powerplay_table():
    """ODI Powerplay Overs Table on Page 48."""
    return TableEvidence(
        table_id="ICC_ODI_MEN_2026:TBL_P48_0",
        source_document_id="ICC_ODI_MEN_2026",
        source_document_sha256="a" * 64,
        source_file_sha256="b" * 64,
        page_number=48,
        printed_page_number=48,
        source_locator="Clause 28.7.2.4 Table",
        caption="Powerplay Overs for Reduced Innings",
        headers=["Innings duration", "Powerplay 1", "Powerplay 2", "Powerplay 3"],
        rows=[
            ["20", "4", "12", "4"],
            ["21", "4", "13", "4"],
            ["22", "5", "13", "4"],
            ["50", "10", "30", "10"]
        ],
        shape=(4, 4),
        units={"Innings duration": "overs", "Powerplay 1": "overs"},
        footnotes=["Innings must be at least 20 overs to constitute a match."],
        linked_clause_ids=["ICC_ODI_MEN_2026:28.7.2.3", "ICC_ODI_MEN_2026:28.7.2.4"],
        validation_status=TableValidationStatus.SOURCE_VERIFIED,
        reviewer_notes="Verified against official ICC Men's ODI Playing Conditions page 48."
    )


def test_table_evidence_exact_cell_and_shape_preservation(table_service, sample_powerplay_table):
    table_service.register_table(sample_powerplay_table)
    retrieved = table_service.get_table_by_id("ICC_ODI_MEN_2026:TBL_P48_0")

    assert retrieved is not None
    assert retrieved.shape == (4, 4)
    assert retrieved.headers == ["Innings duration", "Powerplay 1", "Powerplay 2", "Powerplay 3"]
    assert retrieved.rows[0] == ["20", "4", "12", "4"]
    assert retrieved.rows[3] == ["50", "10", "30", "10"]


def test_table_evidence_null_vs_empty_string_preservation(table_service):
    table = TableEvidence(
        table_id="TEST_DOC:TBL_NULLS",
        source_document_id="TEST_DOC",
        page_number=1,
        headers=["Col1", "Col2", "Col3"],
        rows=[
            [None, "", "ValidText"],
            ["Row2A", None, ""]
        ],
        shape=(2, 3),
        linked_clause_ids=["TEST_DOC:1.1"],
        validation_status=TableValidationStatus.SOURCE_VERIFIED
    )
    table_service.register_table(table)

    retrieved = table_service.get_table_by_id("TEST_DOC:TBL_NULLS")
    assert retrieved is not None
    # Verify strict preservation of None vs empty string
    assert retrieved.rows[0][0] is None
    assert retrieved.rows[0][1] == ""
    assert retrieved.rows[0][2] == "ValidText"
    assert retrieved.rows[1][1] is None
    assert retrieved.rows[1][2] == ""


def test_table_evidence_units_and_footnotes_preservation(table_service, sample_powerplay_table):
    table_service.register_table(sample_powerplay_table)
    retrieved = table_service.get_table_by_id("ICC_ODI_MEN_2026:TBL_P48_0")

    assert retrieved.units == {"Innings duration": "overs", "Powerplay 1": "overs"}
    assert retrieved.footnotes == ["Innings must be at least 20 overs to constitute a match."]


def test_table_evidence_non_source_verified_exclusion(table_service):
    frag_table = TableEvidence(
        table_id="ICC_ODI_MEN_2026:TBL_FRAG",
        source_document_id="ICC_ODI_MEN_2026",
        page_number=78,
        headers=["A", "B"],
        rows=[["", ""]],
        shape=(1, 2),
        linked_clause_ids=["ICC_ODI_MEN_2026:99.1"],
        validation_status=TableValidationStatus.DEPRECATED_FRAGMENT
    )
    table_service.register_table(frag_table)

    # Must NOT be in active index
    assert table_service.get_table_by_id("ICC_ODI_MEN_2026:TBL_FRAG") is None

    # Must NOT be returned via clause hydration
    hydrated = table_service.get_table_evidence_for_clause(
        clause_id="ICC_ODI_MEN_2026:99.1",
        candidate_document_ids=["ICC_ODI_MEN_2026"]
    )
    assert len(hydrated) == 0


def test_table_evidence_duplicate_id_rejection(table_service, sample_powerplay_table):
    table_service.register_table(sample_powerplay_table)
    with pytest.raises(ValueError, match="Duplicate table ID rejected"):
        table_service.register_table(sample_powerplay_table)


def test_table_evidence_candidate_bundle_confinement(table_service, sample_powerplay_table):
    table_service.register_table(sample_powerplay_table)

    # In-bundle match (ICC_ODI_MEN_2026 present in candidates)
    hydrated = table_service.get_table_evidence_for_clause(
        clause_id="ICC_ODI_MEN_2026:28.7.2.4",
        candidate_document_ids=["ICC_ODI_MEN_2026", "MCC_LAWS_2026"]
    )
    assert len(hydrated) == 1
    assert hydrated[0].table_id == "ICC_ODI_MEN_2026:TBL_P48_0"

    # Out-of-bundle blocking (T20I query attempting to retrieve ODI table)
    blocked = table_service.get_table_evidence_for_clause(
        clause_id="ICC_ODI_MEN_2026:28.7.2.4",
        candidate_document_ids=["ICC_T20I_MEN_2026", "MCC_LAWS_2026"]
    )
    assert len(blocked) == 0


def test_table_evidence_format_and_gender_isolation(table_service, sample_powerplay_table):
    table_service.register_table(sample_powerplay_table)

    women_odi_table = TableEvidence(
        table_id="ICC_ODI_WOMEN_2026:TBL_P48_0",
        source_document_id="ICC_ODI_WOMEN_2026",
        page_number=48,
        headers=["Innings duration", "Powerplay 1", "Powerplay 2"],
        rows=[["20", "4", "12"]],
        shape=(1, 3),
        linked_clause_ids=["ICC_ODI_WOMEN_2026:28.7.2.4"],
        validation_status=TableValidationStatus.SOURCE_VERIFIED
    )
    table_service.register_table(women_odi_table)

    # Men's query only receives Men's table
    mens_res = table_service.get_table_evidence_for_clause(
        clause_id="ICC_ODI_MEN_2026:28.7.2.4",
        candidate_document_ids=["ICC_ODI_MEN_2026"]
    )
    assert len(mens_res) == 1
    assert mens_res[0].table_id == "ICC_ODI_MEN_2026:TBL_P48_0"

    # Women's query only receives Women's table
    womens_res = table_service.get_table_evidence_for_clause(
        clause_id="ICC_ODI_WOMEN_2026:28.7.2.4",
        candidate_document_ids=["ICC_ODI_WOMEN_2026"]
    )
    assert len(womens_res) == 1
    assert womens_res[0].table_id == "ICC_ODI_WOMEN_2026:TBL_P48_0"


def test_table_evidence_markdown_rendering(table_service, sample_powerplay_table):
    table_service.register_table(sample_powerplay_table)
    md = table_service.render_markdown(sample_powerplay_table)

    assert "### Regulatory Specification: Powerplay Overs for Reduced Innings" in md
    assert "Document: ICC_ODI_MEN_2026 | Page: 48 | Table ID: `ICC_ODI_MEN_2026:TBL_P48_0`" in md
    assert "| Innings duration | Powerplay 1 | Powerplay 2 | Powerplay 3 |" in md
    assert "| 20 | 4 | 12 | 4 |" in md
    assert "> Note: Innings must be at least 20 overs to constitute a match." in md


def test_table_evidence_numeric_claim_validation(table_service, sample_powerplay_table):
    table_service.register_table(sample_powerplay_table)

    # 20 overs -> Powerplay 1 is 4 overs
    assert table_service.validate_numeric_claim(
        sample_powerplay_table,
        row_criteria={"Innings duration": "20"},
        target_column="Powerplay 1",
        expected_value="4"
    ) is True

    # 20 overs -> Powerplay 2 is 12 overs
    assert table_service.validate_numeric_claim(
        sample_powerplay_table,
        row_criteria={"Innings duration": "20"},
        target_column="Powerplay 2",
        expected_value="12"
    ) is True

    # 22 overs -> Powerplay 1 is 5 overs (not 4)
    assert table_service.validate_numeric_claim(
        sample_powerplay_table,
        row_criteria={"Innings duration": "22"},
        target_column="Powerplay 1",
        expected_value="4"
    ) is False


@pytest.fixture
def memory_repo():
    from sqlalchemy.orm import Session
    from cricketiq.backend.app.database.connection import create_db_engine
    from cricketiq.backend.app.database.orm_models import Base
    from cricketiq.backend.app.database.repository import CricketIQRepository

    engine = create_db_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = Session(bind=engine)
    return CricketIQRepository(session)


def test_table_evidence_auto_load_from_corpus(memory_repo):
    """Verify live loading against data/corpus/manifests/gate3_table_audit.json."""
    live_service = TableEvidenceService(repository=memory_repo, auto_load=True)
    # Check that exactly 246 total tables were audited
    assert len(live_service._all_audited_tables) == 246
    # Check that exactly 39 active Playing Conditions tables are SOURCE_VERIFIED
    assert len(live_service._tables_by_id) == 39
    assert all(t.validation_status == TableValidationStatus.SOURCE_VERIFIED for t in live_service._tables_by_id.values())


def test_unrelated_clauses_same_page_do_not_share_table():
    """Verify that sharing a page number does not grant table linkage without explicit audit."""
    service = TableEvidenceService(auto_load=False)
    # Register a verified table linked ONLY to Clause A on page 48
    table = TableEvidence(
        table_id="ICC_ODI_MEN_2026:TBL_P48_0",
        source_document_id="ICC_ODI_MEN_2026",
        source_file_sha256="abc123",
        page_number=48,
        headers=["Over", "Fielders"],
        rows=[["1-10", "2"], ["11-40", "4"]],
        shape=(2, 2),
        linked_clause_ids=["ICC_ODI_MEN_2026:28.7.2.3"],
        validation_status=TableValidationStatus.SOURCE_VERIFIED
    )
    service.register_table(table)

    # Clause A (explicitly linked) must receive the table
    results_a = service.get_table_evidence_for_clause("ICC_ODI_MEN_2026:28.7.2.3", ["ICC_ODI_MEN_2026"])
    assert len(results_a) == 1
    assert results_a[0].table_id == "ICC_ODI_MEN_2026:TBL_P48_0"

    # Clause B (unrelated clause on page 48, not linked in audit) must NOT receive the table
    results_b = service.get_table_evidence_for_clause("ICC_ODI_MEN_2026:12.1.1", ["ICC_ODI_MEN_2026"])
    assert len(results_b) == 0


def test_table_evidence_metadata_preservation(memory_repo):
    """Verify that auto-loaded tables preserve all structural metadata."""
    service = TableEvidenceService(repository=memory_repo, auto_load=True)
    table = service.get_table_by_id("ICC_ODI_MEN_2026:TBL_P48_0")
    assert table is not None
    assert table.source_document_id == "ICC_ODI_MEN_2026"
    assert table.page_number == 48
    assert table.shape == (31, 4)
    assert table.source_file_sha256 is not None
    assert len(table.source_file_sha256) == 64
    assert table.validation_status == TableValidationStatus.SOURCE_VERIFIED
    assert len(table.linked_clause_ids) >= 1
    assert "ICC_ODI_MEN_2026:28.7.2.3" in table.linked_clause_ids
    # Verify exact cell layout
    assert table.headers == ["Innings duration", "Powerplay 1", "Powerplay 2", "Powerplay 3"]
    assert table.rows[0] == ["20", "4", "12", "4"]

