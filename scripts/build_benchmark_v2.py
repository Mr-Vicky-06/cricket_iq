#!/usr/bin/env python3
"""Build Expanded Benchmark v2 for CricketIQ Retrieval Subsystem.

Combines:
1. All 65 regression items from benchmark_v1.jsonl (marked with benchmark_version="v2")
2. Curated expansion items covering:
   - MCC Laws (Timed out, LBW, Run out, Mankad/38.3, Obstructing field, Hit ball twice, Dead ball, Boundaries)
   - Test Playing Conditions (Follow-on, 90 overs, new ball after 80 overs, no Free Hit)
   - ODI Playing Conditions (50 overs, 10 overs/bowler, 3 Powerplays, Free Hit, DLS rain interruption)
   - T20I Playing Conditions (20 overs, 4 overs/bowler, 6-over Powerplay, Super Over)
   - Women's Playing Conditions (Ball weight/circumference differences, boundary distance limits)
   - Historical & Transition rules (Series started before Oct 1, 2026 vs series started after)
   - Out-of-Scope queries (IPL Impact Player, BBL Power Surge, PSL regulations, local club cricket)
   - Ambiguous queries requiring clarification

Writes:
- evaluation/retrieval/benchmark_v2.jsonl
"""

import json
import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

EXPANSION_ITEMS = [
    # --- MCC LAWS BASELINE ---
    {
        "question_id": "mcc_law_001",
        "question": "How much time does a new batter have to take guard before being timed out under MCC Laws?",
        "category": "mcc_laws",
        "match_context": {"cricket_level": "universal", "format": None, "category": "Universal"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["31.1", "31"],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "MCC Law 31 sets a 3 minute limit from the fall of a wicket."
    },
    {
        "question_id": "mcc_law_002",
        "question": "Can a bowler run out the non-striker before releasing the delivery under current cricket laws?",
        "category": "mcc_laws",
        "match_context": {"cricket_level": "universal", "format": None, "category": "Universal"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["38.3", "38.1"],
        "expected_supporting_clause_numbers": ["38"],
        "forbidden_clause_numbers": [],
        "notes": "Law 38.3 permits bowler to run out non-striker leaving ground early."
    },
    {
        "question_id": "mcc_law_003",
        "question": "What is the rule when a batter hits the ball twice to protect their stumps?",
        "category": "mcc_laws",
        "match_context": {"cricket_level": "universal", "format": None, "category": "Universal"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["34.1", "34"],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "Law 34 permits second hit solely to guard the wicket."
    },
    {
        "question_id": "mcc_law_004",
        "question": "When does a ball become dead automatically according to the Laws of Cricket?",
        "category": "mcc_laws",
        "match_context": {"cricket_level": "universal", "format": None, "category": "Universal"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["20.1", "20"],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "Law 20.1 governs ball settling in keeper or bowler hands, boundary, or dismissal."
    },
    {
        "question_id": "mcc_law_005",
        "question": "Can a fielder catch the ball while touching the ground outside the boundary rope?",
        "category": "mcc_laws",
        "match_context": {"cricket_level": "universal", "format": None, "category": "Universal"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["19.5", "19"],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "Law 19.5 requires first contact after airborne jump to originate inside boundary."
    },
    {
        "question_id": "mcc_law_006",
        "question": "What penalty is awarded if a batter deliberately runs a short run?",
        "category": "mcc_laws",
        "match_context": {"cricket_level": "universal", "format": None, "category": "Universal"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["18.5", "18"],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "Law 18.5 awards 5 penalty runs to the fielding side for deliberate short run."
    },
    {
        "question_id": "mcc_law_007",
        "question": "How many on-side fielders are permitted behind the popping crease at the moment of delivery?",
        "category": "mcc_laws",
        "match_context": {"cricket_level": "universal", "format": None, "category": "Universal"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["28.4", "28"],
        "expected_supporting_clause_numbers": ["21.1"],
        "forbidden_clause_numbers": [],
        "notes": "Law 28.4 limits behind-crease leg-side fielders to a maximum of 2; breach is No ball."
    },
    {
        "question_id": "mcc_law_008",
        "question": "What constitutes fair delivery of the ball with respect to the bowler's arm?",
        "category": "mcc_laws",
        "match_context": {"cricket_level": "universal", "format": None, "category": "Universal"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["21.2", "21"],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "Law 21.2 fair delivery requires arm not to be thrown."
    },

    # --- TEST PLAYING CONDITIONS ---
    {
        "question_id": "test_pc_001",
        "question": "How many runs lead must a team have to enforce the follow-on in a 5-day Men's Test match?",
        "category": "test_regulations",
        "match_context": {"cricket_level": "international", "format": "Test", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["14.1", "14"],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": ["21.18"],
        "notes": "Clause 14.1 mandates 200 runs lead in a 5-day Test match."
    },
    {
        "question_id": "test_pc_002",
        "question": "When can the fielding captain take a new ball in a Men's Test match?",
        "category": "test_regulations",
        "match_context": {"cricket_level": "international", "format": "Test", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["4.3", "4"],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": ["21.18"],
        "notes": "Clause 4.3 permits new ball after 80 overs."
    },
    {
        "question_id": "test_pc_003",
        "question": "How many overs is a team required to bowl per day in a Test match?",
        "category": "test_regulations",
        "match_context": {"cricket_level": "international", "format": "Test", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["12.7", "12"],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": ["21.18"],
        "notes": "Minimum 90 overs per day scheduled."
    },
    {
        "question_id": "test_pc_004",
        "question": "Does bowling a front-foot no ball give a free hit in Test cricket?",
        "category": "test_regulations",
        "match_context": {"cricket_level": "international", "format": "Test", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["21.1"],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": ["21.18", "21.18.1", "21.18.2"],
        "notes": "Test match PC do not contain Free Hit Clause 21.18."
    },

    # --- ODI PLAYING CONDITIONS ---
    {
        "question_id": "odi_pc_001",
        "question": "What is the maximum number of overs a bowler can bowl in an uninterrupted Men's ODI?",
        "category": "odi_regulations",
        "match_context": {"cricket_level": "international", "format": "ODI", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["13.9", "13"],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "Clause 13.9 limits bowlers to 10 overs (20% of 50 overs)."
    },
    {
        "question_id": "odi_pc_002",
        "question": "How many fielders are allowed outside the 30-yard circle in the first 10 overs of an ODI?",
        "category": "odi_regulations",
        "match_context": {"cricket_level": "international", "format": "ODI", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["28.7", "28"],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "Powerplay 1 (overs 1-10) permits maximum 2 fielders outside circle."
    },
    {
        "question_id": "odi_pc_003",
        "question": "Does a bowler bowling a no ball award a free hit in One Day Internationals?",
        "category": "odi_regulations",
        "match_context": {"cricket_level": "international", "format": "ODI", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["21.18", "21.18.1"],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "Clause 21.18 in ODI PC mandates a Free Hit delivery."
    },
    {
        "question_id": "odi_pc_004",
        "question": "How is a revised target calculated when rain interrupts a 50-over ODI match?",
        "category": "odi_regulations",
        "match_context": {"cricket_level": "international", "format": "ODI", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["16.4", "16"],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "Clause 16.4 prescribes the Duckworth-Lewis-Stern (DLS) method."
    },

    # --- T20I PLAYING CONDITIONS ---
    {
        "question_id": "t20i_pc_001",
        "question": "What is the maximum number of overs a bowler can bowl in an uninterrupted Men's T20I match?",
        "category": "t20i_regulations",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["13.9", "13"],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "Clause 13.9 limits bowlers to 4 overs (20% of 20 overs)."
    },
    {
        "question_id": "t20i_pc_002",
        "question": "How long is the mandatory powerplay at the start of a Twenty20 International innings?",
        "category": "t20i_regulations",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["28.7", "28"],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "Powerplay is 6 overs in uninterrupted 20-over innings."
    },
    {
        "question_id": "t20i_pc_003",
        "question": "How is a tied match resolved in a Twenty20 International?",
        "category": "t20i_regulations",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["16.5", "16"],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "Clause 16.5 prescribes a Super Over procedure."
    },

    # --- WOMEN'S PLAYING CONDITIONS ---
    {
        "question_id": "women_pc_001",
        "question": "What is the official weight and circumference of the ball used in Women's International cricket?",
        "category": "gender_category",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Women's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["4.2", "4"],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "Clause 4.2 in Women's PC modifies Law 4.2: ball weighs 4.94 to 5.31 oz."
    },
    {
        "question_id": "women_pc_002",
        "question": "What are the boundary distance limits in Women's Twenty20 International matches?",
        "category": "gender_category",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Women's", "series_start_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["19.1", "19"],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "Clause 19.1 sets Women's boundary limits between 55 and 65 yards."
    },

    # --- HISTORICAL & TRANSITION CASES ---
    {
        "question_id": "hist_trans_001",
        "question": "Which playing conditions govern a bilateral series that began on 25 September 2026 with a match on 3 October 2026?",
        "category": "temporal_applicability",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-09-25", "match_date": "2026-10-03"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["21.18"],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "Series started before 1 October 2026; predecessor regulations apply."
    },
    {
        "question_id": "hist_trans_002",
        "question": "Which rules apply to a match played on 5 October 2026 in a series that started on 2 October 2026?",
        "category": "temporal_applicability",
        "match_context": {"cricket_level": "international", "format": "T20I", "category": "Men's", "series_start_date": "2026-10-02", "match_date": "2026-10-05"},
        "expected_status": "SUCCESS",
        "expected_primary_clause_numbers": ["21.18"],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "Series started after 1 October 2026; October 2026 regulations apply."
    },

    # --- OUT OF SCOPE / NEGATIVE CASES ---
    {
        "question_id": "out_of_scope_001",
        "question": "How does the Impact Player substitution rule work in the Indian Premier League?",
        "category": "out_of_scope",
        "match_context": {"cricket_level": "domestic", "competition": "IPL", "format": "T20I", "category": "Men's"},
        "expected_status": "BLOCKED_OUT_OF_SCOPE",
        "expected_primary_clause_numbers": [],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": ["21.18", "21.1"],
        "notes": "IPL domestic franchise regulations are strictly out of MVP scope."
    },
    {
        "question_id": "out_of_scope_002",
        "question": "What is the Power Surge rule in the Big Bash League?",
        "category": "out_of_scope",
        "match_context": {"cricket_level": "domestic", "competition": "BBL", "format": "T20I", "category": "Men's"},
        "expected_status": "BLOCKED_OUT_OF_SCOPE",
        "expected_primary_clause_numbers": [],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "BBL franchise rule out of MVP scope."
    },
    {
        "question_id": "out_of_scope_003",
        "question": "Can a player be substituted under PSL local tournament conditions?",
        "category": "out_of_scope",
        "match_context": {"cricket_level": "domestic", "competition": "PSL", "format": "T20I", "category": "Men's"},
        "expected_status": "BLOCKED_OUT_OF_SCOPE",
        "expected_primary_clause_numbers": [],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "PSL out of MVP scope."
    },
    {
        "question_id": "ambiguous_001",
        "question": "How many overs are played in a match?",
        "category": "requires_clarification",
        "match_context": {"cricket_level": "international", "format": None, "category": None},
        "expected_status": "REQUIRES_CLARIFICATION",
        "expected_primary_clause_numbers": [],
        "expected_supporting_clause_numbers": [],
        "forbidden_clause_numbers": [],
        "notes": "Cannot determine whether Test (unlimited/90 per day), ODI (50), or T20I (20)."
    }
]

def main():
    b1_path = root_dir / "evaluation" / "retrieval" / "benchmark_v1.jsonl"
    b2_path = root_dir / "evaluation" / "retrieval" / "benchmark_v2.jsonl"

    if not b1_path.exists():
        print(f"Error: {b1_path} not found")
        sys.exit(1)

    with open(b1_path, "r", encoding="utf-8") as f:
        v1_items = [json.loads(line) for line in f if line.strip()]

    print(f"Loaded {len(v1_items)} baseline items from benchmark_v1.jsonl.")

    # Tag v1 items with benchmark_version="v2"
    all_items = []
    for item in v1_items:
        item["benchmark_version"] = "v2"
        all_items.append(item)

    # Add expansion items
    for item in EXPANSION_ITEMS:
        item["benchmark_version"] = "v2"
        all_items.append(item)

    with open(b2_path, "w", encoding="utf-8") as f:
        for item in all_items:
            f.write(json.dumps(item) + "\n")

    print(f"Successfully generated benchmark_v2.jsonl: {len(all_items)} total queries ({len(v1_items)} v1 + {len(EXPANSION_ITEMS)} new expansion items).")

if __name__ == "__main__":
    main()
