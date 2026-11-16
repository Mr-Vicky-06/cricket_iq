"""Tests for Multi-View Text Normalization and Segmentation in CricketIQ."""

import pytest
from cricketiq.backend.app.nlp.normalizer import TextNormalizer, NORMALIZATION_VERSION, PIPELINE_VERSION


@pytest.fixture
def normalizer():
    return TextNormalizer()


def test_build_all_seven_views(normalizer):
    raw_clause = (
        "21.18.2 For any free hit, the striker can be dismissed only under the circumstances that "
        "apply for a No ball, even if the delivery for the free hit is called Wide ball. "
        "The striker can therefore be dismissed only under Law 34 (Hit the ball twice), "
        "Law 37 (Obstructing the field) or Law 38 (Run out)."
    )

    record = normalizer.build_views(
        clause_id="ICC_T20I_MEN_2026:21.18.2",
        source_document_id="ICC_T20I_MEN_2026",
        clause_number="21.18.2",
        heading="Free Hit Dismissals",
        original_text=raw_clause,
        authority="ICC",
        document_title="ICC Men's T20I Playing Conditions",
        edition="October 2026",
        page_start=38,
        parent_clause_id="ICC_T20I_MEN_2026:21.18",
        parent_clause_text="21.18 Free Hit",
        clause_type="EXCEPTION"
    )

    # 1. Check metadata and immutability
    assert record.clause_id == "ICC_T20I_MEN_2026:21.18.2"
    assert record.pipeline_version == PIPELINE_VERSION
    assert record.normalization_version == NORMALIZATION_VERSION
    assert len(record.source_text_hash) == 64
    assert record.original_text == raw_clause

    # 2. Check normalized text preserves critical legal tokens
    norm = record.normalized_text
    assert "only under the circumstances" in norm
    assert "Law 34" in norm
    assert "Law 37" in norm
    assert "Law 38" in norm
    assert "No ball" in norm or "no-ball" in norm

    # 3. Check lexical text contains expanded search tokens
    lex = record.lexical_text
    assert "clause 21.18.2" in lex
    assert "law 21" in lex
    assert "free hit" in lex
    assert "free-hit" in lex  # Expanded compound
    assert "no-ball" in lex or "no ball" in lex

    # 4. Check embedding text contextual formatting
    emb = record.embedding_text
    assert "[ICC ICC Men's T20I Playing Conditions | October 2026]" in emb
    assert "Clause 21.18.2 (Free Hit Dismissals):" in emb

    # 5. Check sentence segmentation
    assert len(record.sentence_segments) >= 2
    assert "21.18.2 For any free hit" in record.sentence_segments[0]["text"]

    # 6. Check chunk representation
    assert len(record.chunks) >= 1
    chunk = record.chunks[0]
    assert chunk["chunk_id"] == "ICC_T20I_MEN_2026:21.18.2#c0"
    assert chunk["parent_clause_id"] == "ICC_T20I_MEN_2026:21.18"
    assert chunk["role"] == "CHILD_EXCEPTION"
    assert "[Context: ICC_T20I_MEN_2026:21.18]" in chunk["chunk_text"]

    # 7. Check display text contains official citation
    disp = record.display_text
    assert "Source: ICC Men's T20I Playing Conditions, Clause 21.18.2 (Page 38)" in disp
    assert "published by ICC" in disp


def test_normalization_preserves_legal_negation_and_modals(normalizer):
    legal_text = (
        "Neither batter can be out Caught or Bowled off a No ball. "
        "The bowler must notify the umpire of a change in mode of delivery. "
        "The umpire shall call and signal No ball unless play is suspended, "
        "except where clause 41.2 applies."
    )
    norm = normalizer.normalize_text(legal_text)

    # Every critical modal and negative condition must be 100% intact
    assert "Neither" in norm
    assert "not" in norm or "No" in norm
    assert "must" in norm
    assert "shall" in norm
    assert "unless" in norm
    assert "except" in norm


def test_sentence_segmentation_respects_cricket_abbreviations(normalizer):
    text_with_abbr = (
        "The bowler must deliver from behind the crease, e.g. the popping crease. "
        "The incoming batter has approx. 3 minutes to take guard. "
        "No player may enter without permission under cl. 24.1."
    )
    sentences = normalizer.segment_sentences(text_with_abbr)

    # Should not split on 'e.g.', 'approx.', or 'cl.'
    assert len(sentences) == 3
    assert "e.g. the popping crease." in sentences[0].text
    assert "approx. 3 minutes to take guard." in sentences[1].text
    assert "under cl. 24.1." in sentences[2].text


def test_lexical_compound_expansion(normalizer):
    text = "A bowler delivered a no-ball resulting in a free-hit delivery."
    lex = normalizer.build_lexical_text(text, clause_number="21.18.1", heading="Free Hit")

    # Both hyphenated and space-separated forms must be present for FTS matching
    assert "no-ball" in lex
    assert "no ball" in lex
    assert "free-hit" in lex
    assert "free hit" in lex
    assert "clause 21.18.1" in lex
    assert "law 21" in lex
