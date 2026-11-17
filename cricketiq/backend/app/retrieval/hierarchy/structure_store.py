"""Structural Hierarchy Node Store for CricketIQ (Phase 6 Gate 3 Task 3.2).

Provides lookup and validation for verified, non-citable structural hierarchy nodes
(such as unnumbered chapter headings) that provide navigational context without
constituting RuleClause legal entities.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, List, Optional

from cricketiq.backend.app.database.models import ClauseStructureNode

PROJECT_ROOT = Path(__file__).resolve().parents[5]
DEFAULT_STRUCTURAL_NODES_PATH = (
    PROJECT_ROOT / "data" / "corpus" / "manifests" / "gate3_structural_nodes.json"
)
DEFAULT_PARENT_MAPPING_PATH = (
    PROJECT_ROOT / "data" / "corpus" / "manifests" / "gate3_parent_mapping.json"
)


class ClauseStructureNodeStore:
    """In-memory index for verified structural hierarchy nodes."""

    def __init__(
        self,
        manifest_path: Optional[Path] = None,
        parent_mapping_path: Optional[Path] = None
    ):
        self.manifest_path = manifest_path or DEFAULT_STRUCTURAL_NODES_PATH
        self.parent_mapping_path = parent_mapping_path or DEFAULT_PARENT_MAPPING_PATH
        self._nodes_by_id: Dict[str, ClauseStructureNode] = {}
        self._nodes_by_doc: Dict[str, List[ClauseStructureNode]] = {}
        self._child_to_structure: Dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        if self.manifest_path.exists():
            with open(self.manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data:
                node = ClauseStructureNode(
                    id=item["id"],
                    source_document_id=item["source_document_id"],
                    heading_title=item["heading_title"],
                    source_locator=item.get("source_locator", ""),
                    page_start=item["page_start"],
                    page_end=item["page_end"],
                    source_provenance=item.get("source_provenance", "ICC Playing Conditions Structural Heading")
                )
                self._nodes_by_id[node.id] = node
                self._nodes_by_doc.setdefault(node.source_document_id, []).append(node)

        if self.parent_mapping_path.exists():
            with open(self.parent_mapping_path, "r", encoding="utf-8") as f:
                mappings = json.load(f)
            for m in mappings:
                if m.get("classification") == "absent_unnumbered_structural_heading":
                    child_id = m.get("child_clause_id")
                    target_id = m.get("proposed_target_id")
                    if child_id and target_id:
                        self._child_to_structure[child_id] = target_id

    def get_node(self, node_id: str) -> Optional[ClauseStructureNode]:
        """Fetch structural node by its unique identifier."""
        return self._nodes_by_id.get(node_id)

    def get_nodes_for_document(self, document_id: str) -> List[ClauseStructureNode]:
        """Fetch all structural nodes belonging to a document."""
        return list(self._nodes_by_doc.get(document_id, []))

    def get_structural_parent(self, child_clause_id: str) -> Optional[ClauseStructureNode]:
        """Fetch structural parent node for a child clause if registered."""
        target_id = self._child_to_structure.get(child_clause_id)
        if target_id:
            return self._nodes_by_id.get(target_id)
        return None

    @property
    def total_nodes(self) -> int:
        return len(self._nodes_by_id)

    @property
    def total_mapped_children(self) -> int:
        return len(self._child_to_structure)
