"""Generates benchmark_v1.jsonl with 65 labelled evaluation items across all 15 required categories.
"""

import json
from pathlib import Path

BENCHMARK_ITEMS = [
    # 1. Exact clause-number lookup (1-10)
    {
        "question_id": "exact_001",
        "question": "What is clause 21.18.2?",
        "category": "exact_clause_number",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["21.18.2"],
        "expected_supporting_clause_numbers": ["21.18", "21.17"],
        "forbidden_clause_numbers": [],
        "notes": "Exact dotted lookup for Free Hit dismissals"
    },
    {
        "question_id": "exact_002",
        "question": "Show me clause 21.18",
        "category": "exact_clause_number",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["21.18"],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "Exact dotted lookup for Free Hit header section"
    },
    {
        "question_id": "exact_003",
        "question": "What is stated in clause 21.17?",
        "category": "exact_clause_number",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["21.17"],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "Exact clause for dismissals from a no-ball"
    },
    {
        "question_id": "exact_004",
        "question": "Clause 21.1 mode of delivery",
        "category": "exact_clause_number",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["21.1"],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "Exact clause for mode of delivery"
    },
    {
        "question_id": "exact_005",
        "question": "What does clause 22.1 say?",
        "category": "exact_clause_number",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["22.1"],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "Exact clause for judging a wide"
    },
    {
        "question_id": "exact_006",
        "question": "Rule 21.18.3 field changes",
        "category": "exact_clause_number",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["21.18.3"],
        "expected_supporting_clause_numbers": ["21.18"],
        "forbidden_clause_numbers": [],
        "notes": "Field changes on free hit"
    },
    {
        "question_id": "exact_007",
        "question": "Law 21.2 fair delivery the arm",
        "category": "exact_clause_number",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["21.2"],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "Bowling action and arm fairness"
    },
    {
        "question_id": "exact_008",
        "question": "Clause 21.5 beamer rule",
        "category": "exact_clause_number",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["21.5"],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "High full-pitched deliveries"
    },
    {
        "question_id": "exact_009",
        "question": "Clause 22.1.2 batter movement",
        "category": "exact_clause_number",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["22.1.2"],
        "expected_supporting_clause_numbers": ["22.1"],
        "forbidden_clause_numbers": [],
        "notes": "Batter moving to make contact with wide ball"
    },
    {
        "question_id": "exact_010",
        "question": "Law 21 No Ball overview",
        "category": "exact_clause_number",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["21"],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "Top-level Law 21 header"
    },

    # 2. Exact cricket phrase lookup (11-16)
    {
        "question_id": "phrase_001",
        "question": "Free Hit",
        "category": "exact_phrase",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["21.18", "21.18.1"],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "Exact phrase search for Free Hit"
    },
    {
        "question_id": "phrase_002",
        "question": "Judging a Wide",
        "category": "exact_phrase",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["22.1"],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "Exact heading phrase for Judging a Wide"
    },
    {
        "question_id": "phrase_003",
        "question": "Mode of delivery",
        "category": "exact_phrase",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["21.1"],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "Exact heading phrase for Mode of delivery"
    },
    {
        "question_id": "phrase_004",
        "question": "High full-pitched deliveries",
        "category": "exact_phrase",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["21.5"],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "Official term for beamers"
    },
    {
        "question_id": "phrase_005",
        "question": "Dismissals from a No ball",
        "category": "exact_phrase",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["21.17"],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "Exact heading phrase for Clause 21.17"
    },
    {
        "question_id": "phrase_006",
        "question": "Fair delivery - the arm",
        "category": "exact_phrase",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["21.2"],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "Exact heading phrase for arm extension"
    },

    # 3. Natural-language paraphrases (17-22)
    {
        "question_id": "nl_001",
        "question": "Can a batter be given out after a front-foot no ball delivery on the free shot?",
        "category": "paraphrase",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["21.18.2"],
        "expected_supporting_clause_numbers": ["21.17"],
        "forbidden_clause_numbers": [],
        "notes": "Paraphrase of free hit dismissals"
    },
    {
        "question_id": "nl_002",
        "question": "What happens if a bowler delivers a full toss above the batter's waist?",
        "category": "paraphrase",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["21.5"],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "Paraphrase of beamer / high full-pitch rule"
    },
    {
        "question_id": "nl_003",
        "question": "Does the umpire call a wide if the ball passes beyond the batter's reach?",
        "category": "paraphrase",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["22.1", "22.1.1"],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "Paraphrase of judging a wide ball"
    },
    {
        "question_id": "nl_004",
        "question": "Must a bowler inform the umpire before switching from right arm to left arm bowling?",
        "category": "paraphrase",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["21.1", "21.1.1"],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "Paraphrase of mode of delivery"
    },
    {
        "question_id": "nl_005",
        "question": "Is the captain allowed to reposition fielders before a free hit ball?",
        "category": "paraphrase",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["21.18.3"],
        "expected_supporting_clause_numbers": ["21.18"],
        "forbidden_clause_numbers": [],
        "notes": "Paraphrase of field changes on free hit"
    },
    {
        "question_id": "nl_006",
        "question": "What is the consequence of bowling an illegal no ball in twenty20?",
        "category": "paraphrase",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["21.18", "21.18.1"],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "Paraphrase of consequence of no-ball"
    },

    # 4. Synonyms and common user wording (23-28)
    {
        "question_id": "syn_001",
        "question": "illegal chucking throw bowling action legality",
        "category": "synonyms",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["21.2"],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "Colloquial term chucking mapped to fair delivery the arm"
    },
    {
        "question_id": "syn_002",
        "question": "beamer above waist dangerous bowling penalty",
        "category": "synonyms",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["21.5"],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "Slang beamer mapped to high full-pitched delivery"
    },
    {
        "question_id": "syn_003",
        "question": "freebie delivery extra runs illegal ball",
        "category": "synonyms",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["21.18", "21.18.1"],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "Slang freebie mapped to free hit"
    },
    {
        "question_id": "syn_004",
        "question": "batter shuffling across stumps wide guideline",
        "category": "synonyms",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["22.1.2"],
        "expected_supporting_clause_numbers": ["22.1"],
        "forbidden_clause_numbers": [],
        "notes": "Batter shuffling mapped to moving to make contact"
    },
    {
        "question_id": "syn_005",
        "question": "bowling round the wicket without telling umpire",
        "category": "synonyms",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["21.1", "21.1.1"],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "Colloquial query for bowling mode"
    },
    {
        "question_id": "syn_006",
        "question": "ways a batter can get out off a no-ball delivery",
        "category": "synonyms",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["21.17"],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "Ways a batter can get out off no ball"
    },

    # 5. Free Hit / No ball cross-clause retrieval (29-34)
    {
        "question_id": "cross_001",
        "question": "Can a batter be run out on a free hit?",
        "category": "cross_clause_composite",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["21.18.2"],
        "expected_supporting_clause_numbers": ["21.17", "21.18"],
        "forbidden_clause_numbers": [],
        "notes": "Primary clause 21.18.2 must expand to 21.17 for run out exception"
    },
    {
        "question_id": "cross_002",
        "question": "Can a batter be dismissed for obstructing the field during a free hit?",
        "category": "cross_clause_composite",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["21.18.2"],
        "expected_supporting_clause_numbers": ["21.17"],
        "forbidden_clause_numbers": [],
        "notes": "Requires cross-reference to Clause 21.17"
    },
    {
        "question_id": "cross_003",
        "question": "What dismissals apply to a free hit?",
        "category": "cross_clause_composite",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["21.18.2"],
        "expected_supporting_clause_numbers": ["21.17"],
        "forbidden_clause_numbers": [],
        "notes": "Requires composite evidence from 21.18.2 and 21.17"
    },
    {
        "question_id": "cross_004",
        "question": "Can a batter hit the ball twice on a free hit?",
        "category": "cross_clause_composite",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["21.18.2"],
        "expected_supporting_clause_numbers": ["21.17"],
        "forbidden_clause_numbers": [],
        "notes": "Requires composite evidence from 21.18.2 and 21.17"
    },
    {
        "question_id": "cross_005",
        "question": "Is caught out possible on a free hit?",
        "category": "cross_clause_composite",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["21.18.2"],
        "expected_supporting_clause_numbers": ["21.17"],
        "forbidden_clause_numbers": [],
        "notes": "Caught out not in 21.17 list"
    },
    {
        "question_id": "cross_006",
        "question": "Can a batter be stumped off a free hit delivery?",
        "category": "cross_clause_composite",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["21.18.2"],
        "expected_supporting_clause_numbers": ["21.17"],
        "forbidden_clause_numbers": [],
        "notes": "Stumped not in 21.17 exceptions"
    },

    # 6. Wide-ball and No-ball interpretation (35-40)
    {
        "question_id": "interp_001",
        "question": "Can a ball be called both a wide and a no ball?",
        "category": "rules_interpretation",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["22.1.1"],
        "expected_supporting_clause_numbers": ["22.1"],
        "forbidden_clause_numbers": [],
        "notes": "22.1.1 states not being a No ball"
    },
    {
        "question_id": "interp_002",
        "question": "If a ball is wide but also a front-foot no ball which call takes precedence?",
        "category": "rules_interpretation",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["22.1.1", "21"],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "No ball takes precedence over Wide"
    },
    {
        "question_id": "interp_003",
        "question": "What if the ball passes over the batter's head?",
        "category": "rules_interpretation",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["22.1", "21.5"],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "Wide vs high full pitch"
    },
    {
        "question_id": "interp_004",
        "question": "Does a ball hitting the batter's bat or person count as a wide?",
        "category": "rules_interpretation",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["22.1", "22.1.1"],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "Contact negates Wide"
    },
    {
        "question_id": "interp_005",
        "question": "When does the umpire consider the ball not to have passed wide?",
        "category": "rules_interpretation",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["22.1.2"],
        "expected_supporting_clause_numbers": ["22.1"],
        "forbidden_clause_numbers": [],
        "notes": "Clause 22.1.2 batter movement"
    },
    {
        "question_id": "interp_006",
        "question": "Is a bouncer passing wide called a wide or a no-ball?",
        "category": "rules_interpretation",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["22.1", "21"],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "Short pitched delivery over head"
    },

    # 7. Parent section context (41-45)
    {
        "question_id": "parent_001",
        "question": "What is the parent section of clause 21.18.2?",
        "category": "parent_context",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["21.18.2"],
        "expected_supporting_clause_numbers": ["21.18"],
        "forbidden_clause_numbers": [],
        "notes": "Verify 21.18 is attached as parent context"
    },
    {
        "question_id": "parent_002",
        "question": "What is the general heading for clause 21.1.1?",
        "category": "parent_context",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["21.1.1"],
        "expected_supporting_clause_numbers": ["21.1"],
        "forbidden_clause_numbers": [],
        "notes": "Verify 21.1 is attached as parent context"
    },
    {
        "question_id": "parent_003",
        "question": "Parent provision for wide judgment clause 22.1.2",
        "category": "parent_context",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["22.1.2"],
        "expected_supporting_clause_numbers": ["22.1"],
        "forbidden_clause_numbers": [],
        "notes": "Verify 22.1 is attached as parent context"
    },
    {
        "question_id": "parent_004",
        "question": "Free Hit field change rules and its parent rule",
        "category": "parent_context",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["21.18.3"],
        "expected_supporting_clause_numbers": ["21.18"],
        "forbidden_clause_numbers": [],
        "notes": "Verify 21.18 is attached as parent context"
    },
    {
        "question_id": "parent_005",
        "question": "Context of clause 22.1.1 in Wide regulations",
        "category": "parent_context",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["22.1.1"],
        "expected_supporting_clause_numbers": ["22.1"],
        "forbidden_clause_numbers": [],
        "notes": "Verify 22.1 is attached as parent context"
    },

    # 8. Test vs T20I isolation (46-50)
    {
        "question_id": "isolation_001",
        "question": "Does a bowler bowling a no-ball award a free hit in a Test match?",
        "category": "format_isolation",
        "match_context": {"cricket_level": "international", "format": "Test", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["21.1"],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": ["21.18", "21.18.1", "21.18.2"],
        "notes": "Test match Playing Conditions do not contain Free Hit Clause 21.18"
    },
    {
        "question_id": "isolation_002",
        "question": "Mode of delivery in Test cricket",
        "category": "format_isolation",
        "match_context": {"cricket_level": "international", "format": "Test", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["21.1"],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "Must return Test PC clause not T20I PC clause"
    },
    {
        "question_id": "isolation_003",
        "question": "Test match no-ball dismissals",
        "category": "format_isolation",
        "match_context": {"cricket_level": "international", "format": "Test", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["21.1"],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": ["21.18"],
        "notes": "Zero leakage of T20I clauses into Test"
    },
    {
        "question_id": "isolation_004",
        "question": "T20I specific rules for no balls",
        "category": "format_isolation",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["21.18"],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "Must return T20I document"
    },
    {
        "question_id": "isolation_005",
        "question": "Test cricket bowler hand notification",
        "category": "format_isolation",
        "match_context": {"cricket_level": "international", "format": "Test", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["21.1"],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": ["21.18"],
        "notes": "Isolation verification"
    },

    # 9. Domestic gating / out of scope (51-55)
    {
        "question_id": "domestic_001",
        "question": "Can a batter be run out on a free hit in the IPL?",
        "category": "domestic_rejection",
        "match_context": {"cricket_level": "domestic", "competition": "IPL"},
        "expected_status": "CLARIFICATION_REQUIRED",
        "expected_primary_clause_numbers": [],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": ["21.18.2"],
        "notes": "Domestic league must be rejected with clarification"
    },
    {
        "question_id": "domestic_002",
        "question": "What are the powerplay rules in Big Bash League (BBL)?",
        "category": "domestic_rejection",
        "match_context": {"cricket_level": "domestic", "competition": "BBL"},
        "expected_status": "CLARIFICATION_REQUIRED",
        "expected_primary_clause_numbers": [],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "BBL must be rejected with clarification"
    },
    {
        "question_id": "domestic_003",
        "question": "Ranji trophy follow on rules",
        "category": "domestic_rejection",
        "match_context": {"cricket_level": "domestic", "competition": "Ranji"},
        "expected_status": "CLARIFICATION_REQUIRED",
        "expected_primary_clause_numbers": [],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "Ranji Trophy rejected with clarification"
    },
    {
        "question_id": "domestic_004",
        "question": "County championship bowling points",
        "category": "domestic_rejection",
        "match_context": {"cricket_level": "domestic", "competition": "County"},
        "expected_status": "CLARIFICATION_REQUIRED",
        "expected_primary_clause_numbers": [],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "County Championship rejected with clarification"
    },
    {
        "question_id": "domestic_005",
        "question": "PSL free hit regulations",
        "category": "domestic_rejection",
        "match_context": {"cricket_level": "domestic", "competition": "PSL"},
        "expected_status": "CLARIFICATION_REQUIRED",
        "expected_primary_clause_numbers": [],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "PSL rejected with clarification"
    },

    # 10. Missing / transition boundary applicability (56-60)
    {
        "question_id": "trans_001",
        "question": "What are the playing conditions for a match on 2026-10-02?",
        "category": "transition_boundary",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "match_date": "2026-10-02"},
        "expected_status": "CLARIFICATION_REQUIRED",
        "expected_primary_clause_numbers": [],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "Match date >= 2026-10-01 without series_start_date triggers clarification"
    },
    {
        "question_id": "trans_002",
        "question": "Match played on 2026-10-01 boundary day",
        "category": "transition_boundary",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "match_date": "2026-10-01"},
        "expected_status": "CLARIFICATION_REQUIRED",
        "expected_primary_clause_numbers": [],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "Boundary day requires series start date confirmation"
    },
    {
        "question_id": "trans_003",
        "question": "Series started on 2026-09-28 and match on 2026-10-03",
        "category": "transition_boundary",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-09-28", "match_date": "2026-10-03"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["21.18"],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "Ongoing series continuing under predecessor regulations"
    },
    {
        "question_id": "trans_004",
        "question": "Series started on 2026-10-02 post transition",
        "category": "transition_boundary",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-10-02", "match_date": "2026-10-03"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["21.18"],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "Post transition series"
    },
    {
        "question_id": "trans_005",
        "question": "Series boundary day starting 2026-10-01",
        "category": "transition_boundary",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-10-01"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["21.18"],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "Series starting on boundary day gets 2026 edition"
    },

    # 11. Punctuation and spelling variations (61-65)
    {
        "question_id": "punct_001",
        "question": "What happens if the bowler bowls a no-ball?",
        "category": "spelling_and_punctuation",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["21.18", "21.17"],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "Hyphenated no-ball with question mark"
    },
    {
        "question_id": "punct_002",
        "question": "Can I get a free-hit after a no ball?",
        "category": "spelling_and_punctuation",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["21.18"],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "Hyphenated free-hit"
    },
    {
        "question_id": "punct_003",
        "question": "Clause 21.18.2: Free-Hit Dismissals",
        "category": "spelling_and_punctuation",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["21.18.2"],
        "expected_supporting_clause_numbers": ["21.18", "21.17"],
        "forbidden_clause_numbers": [],
        "notes": "Colon and dotted numbers"
    },
    {
        "question_id": "punct_004",
        "question": "is wide-ball judged if batter moves?",
        "category": "spelling_and_punctuation",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["22.1.2"],
        "expected_supporting_clause_numbers": ["22.1"],
        "forbidden_clause_numbers": [],
        "notes": "Hyphenated wide-ball lowercase"
    },
    {
        "question_id": "punct_005",
        "question": "Law-21.1 (Mode of delivery)???",
        "category": "spelling_and_punctuation",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["21.1"],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "Parentheses and triple question marks"
    }
]


def main():
    out_dir = Path("evaluation/retrieval")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "benchmark_v1.jsonl"

    with open(out_path, "w", encoding="utf-8") as f:
        for item in BENCHMARK_ITEMS:
            f.write(json.dumps(item) + "\n")

    print(f"Generated {len(BENCHMARK_ITEMS)} benchmark items to {out_path}")


if __name__ == "__main__":
    main()
