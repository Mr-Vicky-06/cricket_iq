"""Deterministic Rule Applicability Engine for CricketIQ.

Pure domain service that evaluates match context, date triggers (including series-start
transition boundaries), scope levels, competition overlays, and explicit document
relationships to return an authoritative Source Bundle without LLM involvement.
"""

from __future__ import annotations
from datetime import datetime, date
from typing import List, Optional, Dict, Any

from cricketiq.backend.app.database.models import (
    MatchContext, ApplicabilityDecision, SourceDocument,
    DocumentRelationship, CricketFormat, GenderCategory,
    ScopeLevel, ApplicabilityBasis, DocumentStatus, DocumentAuthority
)
from cricketiq.backend.app.database.repository import RuleCatalog

OCT_2026_TRANSITION_DATE = date(2026, 10, 1)


class ApplicabilityEngine:
    """Pure domain service for deterministic cricket rule applicability resolution."""

    def __init__(self, engine_version: str = "2.0.0"):
        self.engine_version = engine_version

    def resolve(self, context: MatchContext, catalog: RuleCatalog) -> ApplicabilityDecision:
        decision_trace: List[str] = []
        reason_codes: List[str] = []
        assumptions: List[str] = []
        unresolved: List[str] = []
        conflicts: List[str] = []
        rejected_candidates: List[Dict[str, str]] = []
        effective_date_basis_used: Dict[str, str] = {}
        relationships_applied: List[DocumentRelationship] = []

        decision_trace.append(f"Engine v{self.engine_version} started resolution.")
        decision_trace.append(f"Input Context: level={context.cricket_level}, format={context.format}, category={context.category}, comp={context.competition}, series_start={context.series_start_date}, match_date={context.match_date}")

        # 1. Domestic vs International Screening
        raw_query = (context.raw_query or "").lower()
        domestic_keywords = ["ipl", "bbl", "psl", "cpl", "vitality blast", "smat", "ranji", "county"]
        is_explicit_domestic = context.cricket_level == "domestic" or any(k in raw_query for k in domestic_keywords)

        if is_explicit_domestic:
            decision_trace.append("Domestic competition identified. Domestic regulations are outside ICC/MCC international corpus.")
            reason_codes.append("DOMESTIC_REGULATION_OUT_OF_SCOPE")
            return ApplicabilityDecision(
                context=context,
                selected_bundle=[],
                is_ambiguous=True,
                clarification_needed=(
                    "Domestic and franchise competitions (such as IPL, BBL, or County Championship) operate under "
                    "their respective board-specific playing conditions. CricketIQ MVP currently covers official ICC "
                    "international playing conditions and MCC Laws. Please specify an international format (Test, ODI, T20I)."
                ),
                reason_codes=reason_codes,
                decision_trace=decision_trace,
                engine_version=self.engine_version
            )

        # 2. Check for missing format when not specified
        if not context.format and not context.competition:
            # Check if query indicates format
            if "t20i" in raw_query or "twenty20 international" in raw_query:
                context.format = CricketFormat.T20I
                assumptions.append("Inferred T20I format from user query text.")
                reason_codes.append("INFERRED_FORMAT_T20I")
            elif "odi" in raw_query or "one day international" in raw_query:
                context.format = CricketFormat.ODI
                assumptions.append("Inferred ODI format from user query text.")
                reason_codes.append("INFERRED_FORMAT_ODI")
            elif "test" in raw_query and "t20" not in raw_query:
                context.format = CricketFormat.TEST
                assumptions.append("Inferred Test format from user query text.")
                reason_codes.append("INFERRED_FORMAT_TEST")
            elif "t20" in raw_query:
                context.format = CricketFormat.T20I
                assumptions.append("Ambiguous 'T20' assumed to refer to international T20I. If you meant domestic (e.g. IPL), rules may differ.")
                reason_codes.append("AMBIGUOUS_T20_DEFAULTED_TO_T20I")

        # 3. Date Boundary Evaluation (Series Start Date vs Match Date)
        series_start_parsed: Optional[date] = None
        match_date_parsed: Optional[date] = None

        if context.series_start_date:
            try:
                series_start_parsed = datetime.strptime(context.series_start_date, "%Y-%m-%d").date()
            except ValueError:
                unresolved.append(f"Invalid series_start_date format: {context.series_start_date}")

        if context.match_date:
            try:
                match_date_parsed = datetime.strptime(context.match_date, "%Y-%m-%d").date()
            except ValueError:
                unresolved.append(f"Invalid match_date format: {context.match_date}")

        # Transition state determination for ICC series-start basis
        target_edition_family: Optional[str] = None  # "2026" or "previous"

        if series_start_parsed is not None:
            if series_start_parsed >= OCT_2026_TRANSITION_DATE:
                target_edition_family = "2026"
                reason_codes.append("SERIES_START_POST_OCT_2026_APPLIES_2026_EDITION")
                decision_trace.append(f"Series start date {series_start_parsed} is >= 2026-10-01. Target edition: October 2026.")
            else:
                target_edition_family = "previous"
                reason_codes.append("SERIES_START_PRE_OCT_2026_APPLIES_PREVIOUS_EDITION")
                decision_trace.append(f"Series start date {series_start_parsed} is < 2026-10-01. Target edition: Previous (ongoing series continues under previous regulations).")
        else:
            # Series start date unknown
            if match_date_parsed is not None:
                if match_date_parsed < OCT_2026_TRANSITION_DATE:
                    target_edition_family = "previous"
                    reason_codes.append("MATCH_DATE_PRE_OCT_2026_APPLIES_PREVIOUS_EDITION")
                    decision_trace.append(f"Match date {match_date_parsed} is < 2026-10-01. Target edition: Previous.")
                else:
                    # Match date is >= 2026-10-01 but series start date is unknown!
                    decision_trace.append(f"Match date {match_date_parsed} is >= 2026-10-01 but series_start_date is missing. Critical transition boundary.")
                    unresolved.append("series_start_date")
                    reason_codes.append("REQUIRES_SERIES_START_DATE_CONFIRMATION")
                    return ApplicabilityDecision(
                        context=context,
                        selected_bundle=[],
                        is_ambiguous=True,
                        unresolved_conditions=["series_start_date"],
                        clarification_needed=(
                            f"The match date {context.match_date} falls after the 1 October 2026 ICC regulatory transition. "
                            "However, under ICC regulations, updated playing conditions apply only to series that started "
                            "on or after 1 October 2026. Matches in ongoing series continue under the previous regulations. "
                            "Please provide the series start date to confirm whether this match is under current or previous playing conditions."
                        ),
                        reason_codes=reason_codes,
                        decision_trace=decision_trace,
                        engine_version=self.engine_version
                    )
            else:
                # Neither series_start_date nor match_date provided
                target_edition_family = "2026"
                assumptions.append("No series start date or match date provided; defaulted to current active edition (October 2026).")
                reason_codes.append("DEFAULTED_TO_CURRENT_ACTIVE_EDITION")
                decision_trace.append("No dates specified. Defaulted to current active edition (October 2026).")

        # 4. Gender Category Handling
        target_category = context.category or GenderCategory.MENS
        if context.category is None:
            assumptions.append("Gender category not specified; defaulted to Men's Playing Conditions.")
            reason_codes.append("DEFAULTED_TO_MENS_CATEGORY")

        # 5. Retrieve Active Documents from Catalog
        all_active_docs = catalog.list_active_documents()
        decision_trace.append(f"Evaluating {len(all_active_docs)} active documents in catalog.")

        selected_competition_doc: Optional[SourceDocument] = None
        selected_addendum_doc: Optional[SourceDocument] = None
        selected_format_doc: Optional[SourceDocument] = None
        selected_mcc_baseline_doc: Optional[SourceDocument] = None

        # 6. Screen Documents by Scope and Edition
        for doc in all_active_docs:
            doc_id = doc.id

            # A. Competition Regulations
            if doc.scope_level == ScopeLevel.COMPETITION_PC:
                if context.competition and context.competition.lower() in (doc.competition or "").lower():
                    selected_competition_doc = doc
                    effective_date_basis_used[doc_id] = doc.applicability_basis.value
                    decision_trace.append(f"Matched Competition PC: {doc_id}")
                else:
                    rejected_candidates.append({"doc_id": doc_id, "reason": "Competition mismatch or no competition specified"})
                continue

            # B. Addenda
            if doc.scope_level == ScopeLevel.ADDENDUM:
                if doc.format == context.format and (target_edition_family in doc.edition or "2026" in doc.edition):
                    selected_addendum_doc = doc
                    effective_date_basis_used[doc_id] = doc.applicability_basis.value
                    decision_trace.append(f"Matched Addendum: {doc_id}")
                else:
                    rejected_candidates.append({"doc_id": doc_id, "reason": "Addendum format or edition mismatch"})
                continue

            # C. Format Playing Conditions
            if doc.scope_level == ScopeLevel.FORMAT_PC:
                if doc.format == context.format and doc.category == target_category:
                    edition_matches = (target_edition_family == "2026" and "2026" in doc.edition) or \
                                      (target_edition_family == "previous" and ("2024" in doc.edition or "2022" in doc.edition))
                    if edition_matches:
                        selected_format_doc = doc
                        effective_date_basis_used[doc_id] = doc.applicability_basis.value
                        decision_trace.append(f"Matched Format PC: {doc_id} ({doc.edition})")
                    else:
                        rejected_candidates.append({"doc_id": doc_id, "reason": f"Edition mismatch. Needed {target_edition_family}, document is {doc.edition}"})
                else:
                    rejected_candidates.append({"doc_id": doc_id, "reason": f"Format/Category mismatch. Needed {context.format}/{target_category}, got {doc.format}/{doc.category}"})
                continue

            # D. Baseline MCC Laws
            if doc.scope_level == ScopeLevel.LAWS_BASELINE or doc.publisher == DocumentAuthority.MCC:
                mcc_edition_matches = (target_edition_family == "2026" and ("2026" in doc.edition or "4th" in doc.edition)) or \
                                      (target_edition_family == "previous" and ("2022" in doc.edition or "3rd" in doc.edition or "2017" in doc.edition))
                if mcc_edition_matches:
                    selected_mcc_baseline_doc = doc
                    effective_date_basis_used[doc_id] = doc.applicability_basis.value
                    decision_trace.append(f"Matched Baseline MCC Laws: {doc_id} ({doc.edition})")
                else:
                    rejected_candidates.append({"doc_id": doc_id, "reason": f"MCC edition mismatch. Needed {target_edition_family}, doc is {doc.edition}"})
                continue

        # 7. Assemble Source Bundle in Precedence Order
        selected_bundle: List[SourceDocument] = []
        if selected_competition_doc:
            selected_bundle.append(selected_competition_doc)
            reason_codes.append(f"PRECEDENCE_1_COMPETITION_{selected_competition_doc.id}")
        if selected_addendum_doc:
            selected_bundle.append(selected_addendum_doc)
            reason_codes.append(f"PRECEDENCE_2_ADDENDUM_{selected_addendum_doc.id}")
        if selected_format_doc:
            selected_bundle.append(selected_format_doc)
            reason_codes.append(f"PRECEDENCE_3_FORMAT_PC_{selected_format_doc.id}")
        if selected_mcc_baseline_doc:
            selected_bundle.append(selected_mcc_baseline_doc)
            reason_codes.append(f"PRECEDENCE_4_MCC_BASELINE_{selected_mcc_baseline_doc.id}")

        # 8. Collect Document Relationships
        for doc in selected_bundle:
            doc_rels = catalog.get_relationships(doc.id)
            for rel in doc_rels:
                # Include relationships connecting members of the bundle
                bundle_ids = {d.id for d in selected_bundle}
                if rel.source_doc_id in bundle_ids or rel.target_doc_id in bundle_ids:
                    if rel not in relationships_applied:
                        relationships_applied.append(rel)
                        decision_trace.append(f"Applied relationship: {rel.source_doc_id} {rel.relationship_type.value} {rel.target_doc_id}")

        # Primary and Baseline doc assignment
        primary_doc = selected_competition_doc or selected_format_doc or selected_mcc_baseline_doc
        baseline_doc = selected_mcc_baseline_doc

        decision_trace.append(f"Resolution complete. Selected bundle size: {len(selected_bundle)}")

        return ApplicabilityDecision(
            context=context,
            selected_bundle=selected_bundle,
            primary_document=primary_doc,
            baseline_document=baseline_doc,
            relationships_applied=relationships_applied,
            rejected_candidates=rejected_candidates,
            effective_date_basis_used=effective_date_basis_used,
            reason_codes=reason_codes,
            assumptions=assumptions,
            unresolved_conditions=unresolved,
            conflicts=conflicts,
            is_ambiguous=False,
            clarification_needed=None,
            decision_trace=decision_trace,
            engine_version=self.engine_version
        )
