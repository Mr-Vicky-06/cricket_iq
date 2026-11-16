"""Tokenization and Linguistic Evaluation Engine for CricketIQ.

Analyzes tokenization behaviors across:
1. Exact Identifier Parser (dotted clause numbers, Law names, ranges).
2. Lexical Search Tokenizer (SQLite FTS5 Porter stemmer vs unstemmed tokenization).
3. Embedding Model Tokenizer (sequence length limits, truncation, token fragmentation).
4. Legal modals, negation words, measurements, and hyphenated cricket compound preservation.
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple


CRICKET_EVAL_SAMPLES = [
    {
        "id": "clause_identifier_dotted",
        "category": "exact_identifiers",
        "text": "Clause 21.18.2 states that for any free hit, the striker can be dismissed only under specific Laws.",
        "expected_identifiers": ["21.18.2"],
        "critical_terms": ["free hit", "striker", "dismissed", "only"]
    },
    {
        "id": "law_reference_major",
        "category": "exact_identifiers",
        "text": "The striker can therefore be dismissed only under Law 34 (Hit the ball twice), Law 37 (Obstructing the field) or Law 38 (Run out).",
        "expected_identifiers": ["Law 34", "Law 37", "Law 38"],
        "critical_terms": ["Law 34", "Law 37", "Law 38", "Run out", "Hit the ball twice", "Obstructing the field"]
    },
    {
        "id": "hyphenated_compounds",
        "category": "domain_compounds",
        "text": "A no-ball delivery shall be followed by a free-hit, unless the match is abandoned or delayed.",
        "expected_identifiers": [],
        "critical_terms": ["no-ball", "free-hit", "unless"]
    },
    {
        "id": "legal_negation_and_modals",
        "category": "legal_semantics",
        "text": "Neither batter can be out Caught or Bowled off a No ball, except under the circumstances of Law 34.",
        "expected_identifiers": ["Law 34"],
        "critical_terms": ["neither", "not", "except", "Caught", "Bowled", "No ball"]
    },
    {
        "id": "measurements_and_times",
        "category": "measurements",
        "text": "The incoming batter must be in position to receive the ball within 3 minutes of the fall of the previous wicket.",
        "expected_identifiers": [],
        "critical_terms": ["must", "3 minutes", "within"]
    },
    {
        "id": "high_full_pitched_delivery",
        "category": "domain_compounds",
        "text": "Any high full-pitched delivery which passes or would have passed above waist height shall be called No ball.",
        "expected_identifiers": [],
        "critical_terms": ["full-pitched", "waist height", "shall", "No ball"]
    }
]


@dataclass
class TokenizationEvalResult:
    sample_id: str
    category: str
    input_text: str
    lexical_tokens: List[str]
    porter_tokens: List[str]
    identifiers_detected: List[str]
    identifiers_preserved: bool
    negation_preserved: bool
    hyphens_handled: bool
    estimated_embedding_tokens: int
    truncation_risk: bool


class TokenizationEvaluator:
    """Evaluates lexical, identifier, and semantic tokenization behaviors."""

    IDENTIFIER_RE = re.compile(
        r"(?:(?:Law|Clause|clause|law)\s+)?([0-9]{1,2}(?:\.[0-9]{1,2}){0,3})",
        re.IGNORECASE
    )

    def __init__(self, max_sequence_length: int = 512):
        self.max_sequence_length = max_sequence_length

    def extract_identifiers(self, text: str) -> List[str]:
        """Extract exact Law numbers and clause references from text."""
        matches = self.IDENTIFIER_RE.findall(text)
        # Deduplicate while preserving order
        seen = set()
        result = []
        for m in matches:
            cleaned = m.strip()
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                result.append(cleaned)
        return result

    def tokenize_lexical(self, text: str) -> List[str]:
        """Simple whitespace and punctuation-split tokenizer for search."""
        cleaned = re.sub(r"[^\w\s\-\.]", " ", text)
        return [tok.strip().lower() for tok in cleaned.split() if tok.strip()]

    def simulate_porter_stemmer(self, tokens: List[str]) -> List[str]:
        """Simulate FTS5 Porter stemmer transformation on representative tokens."""
        stemmed = []
        for tok in tokens:
            t = tok
            if t.endswith("ies") and len(t) > 4:
                t = t[:-3] + "y"
            elif t.endswith("es") and len(t) > 3:
                t = t[:-2]
            elif t.endswith("s") and not t.endswith("ss") and len(t) > 2:
                t = t[:-1]
            elif t.endswith("ed") and len(t) > 3:
                t = t[:-2]
            elif t.endswith("ing") and len(t) > 4:
                t = t[:-3]
            stemmed.append(t)
        return stemmed

    def evaluate_sample(self, sample: Dict[str, Any]) -> TokenizationEvalResult:
        """Run tokenization diagnostics on a test sample."""
        text = sample["text"]
        lex_tokens = self.tokenize_lexical(text)
        porter_tokens = self.simulate_porter_stemmer(lex_tokens)
        detected_ids = self.extract_identifiers(text)

        # Check if all expected clause numbers are detected
        expected_ids = sample.get("expected_identifiers", [])
        ids_preserved = True
        for eid in expected_ids:
            # normalize eid (e.g. "Law 34" -> "34")
            raw_num = eid.replace("Law", "").replace("Clause", "").strip()
            if raw_num not in detected_ids:
                ids_preserved = False
                break

        # Check negation preservation (critical words: not, neither, unless, except, only)
        negation_words = {"not", "neither", "unless", "except", "only", "no"}
        present_negation = [w for w in text.lower().split() if w in negation_words]
        negation_preserved = all(w in lex_tokens for w in present_negation)

        # Check hyphen handling (e.g. no-ball or free-hit)
        hyphen_terms = [t for t in sample.get("critical_terms", []) if "-" in t]
        hyphens_handled = True
        if hyphen_terms:
            for ht in hyphen_terms:
                if ht.lower() not in lex_tokens and ht.replace("-", " ").lower() not in " ".join(lex_tokens):
                    hyphens_handled = False
                    break

        # Embedding token estimation (rough heuristic: ~1.3 tokens per word)
        word_count = len(text.split())
        est_tokens = int(word_count * 1.3)
        truncation_risk = est_tokens > self.max_sequence_length

        return TokenizationEvalResult(
            sample_id=sample["id"],
            category=sample["category"],
            input_text=text,
            lexical_tokens=lex_tokens,
            porter_tokens=porter_tokens,
            identifiers_detected=detected_ids,
            identifiers_preserved=ids_preserved,
            negation_preserved=negation_preserved,
            hyphens_handled=hyphens_handled,
            estimated_embedding_tokens=est_tokens,
            truncation_risk=truncation_risk
        )

    def evaluate_all(self, samples: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Run tokenization evaluation across all benchmark samples."""
        eval_samples = samples or CRICKET_EVAL_SAMPLES
        results = [self.evaluate_sample(s) for s in eval_samples]

        total = len(results)
        ids_preserved_count = sum(1 for r in results if r.identifiers_preserved)
        negation_preserved_count = sum(1 for r in results if r.negation_preserved)
        hyphens_handled_count = sum(1 for r in results if r.hyphens_handled)
        truncation_count = sum(1 for r in results if r.truncation_risk)

        return {
            "total_samples": total,
            "identifier_preservation_rate": (ids_preserved_count / max(1, total)) * 100.0,
            "negation_preservation_rate": (negation_preserved_count / max(1, total)) * 100.0,
            "hyphen_compound_handling_rate": (hyphens_handled_count / max(1, total)) * 100.0,
            "truncation_risk_rate": (truncation_count / max(1, total)) * 100.0,
            "sample_results": [
                {
                    "sample_id": r.sample_id,
                    "category": r.category,
                    "identifiers_detected": r.identifiers_detected,
                    "identifiers_preserved": r.identifiers_preserved,
                    "negation_preserved": r.negation_preserved,
                    "hyphens_handled": r.hyphens_handled,
                    "estimated_embedding_tokens": r.estimated_embedding_tokens
                }
                for r in results
            ]
        }
