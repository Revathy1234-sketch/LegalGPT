"""Ground risk findings in verbatim PDF proof.

Risk findings produced by the LLM sometimes omit `source_text` (older prompt
variants returned `citations` / chunk ids instead). This module backfills:

1. quoted passages extracted from the finding's own `citations` (fast), or
2. a semantic retrieval pass against the contract's chunks (fallback),

and fills sensible `page` / `section` values so the frontend Evidence Panel
can always show the exact text each finding is based on.
"""

import re
from typing import Any, Dict, List, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

QUOTE_RE = re.compile(r'[“""]([^”""]{25,})[”""]')


def _quote_from_citations(citations: Any) -> str:
    """Extract verbatim quoted passages from citation strings/objects."""
    texts: List[str] = []
    if not isinstance(citations, list):
        return ""
    for citation in citations:
        if isinstance(citation, str):
            for match in QUOTE_RE.findall(citation):
                cleaned = match.strip().rstrip(".").strip()
                if len(cleaned) >= 25:
                    texts.append(cleaned)
        elif isinstance(citation, dict):
            candidate = (
                citation.get("text")
                or citation.get("content")
                or citation.get("preview")
                or citation.get("content_preview")
                or ""
            )
            if len(str(candidate)) >= 25:
                texts.append(str(candidate).strip())
    return " ".join(texts)[:600]


def _retrieve_proof(db: Session, contract_id: Any, finding: Dict[str, Any]) -> str:
    """Fallback: fetch the document chunk that best matches this finding.

    Uses the browse-mode retriever (no semantic embedding pass) so grounding
    stays fast enough to run inside a request.
    """
    query = " ".join(
        part
        for part in [
            str(finding.get("clause_reference") or ""),
            str(finding.get("category") or ""),
            str(finding.get("issue") or ""),
        ]
        if part
    ).strip()[:200]
    if not query:
        return ""
    try:
        from app.agents.retrieval_agent import retrieve as retrieve_contract_context

        retrieval = retrieve_contract_context(str(contract_id), query, top_k=1)
        chunks = retrieval.get("chunks") or []
        if chunks:
            chunk = chunks[0]
            text = str(
                chunk.get("parent_text")
                or chunk.get("child_text")
                or chunk.get("content")
                or ""
            ).strip()
            if text:
                return text[:600]
    except Exception:  # noqa: BLE001 - grounding must never break analysis
        return ""
    return ""


def ground_risk_matrix(
    db: Session,
    contract_id: Any,
    matrix: Any,
) -> Tuple[Any, bool]:
    """Fill missing `source_text` / `page` / `section` on risk findings.

    Returns (matrix, changed). `changed` is True when anything was written,
    so callers can persist the enriched matrix once.
    """
    if not isinstance(matrix, list) or not matrix:
        return matrix, False

    changed = False
    for finding in matrix:
        if not isinstance(finding, dict):
            continue

        current = str(finding.get("source_text") or "").strip()
        if not current and not finding.get("_proof_searched"):
            proof = _quote_from_citations(finding.get("citations"))
            if not proof:
                proof = _retrieve_proof(db, contract_id, finding)
            if proof:
                finding["source_text"] = proof
                changed = True
            else:
                # Record the attempt so we never pay for a second retrieval
                # pass on an already-processed finding.
                finding["source_text"] = ""
                finding["_proof_searched"] = True
                changed = True

        if not finding.get("page"):
            finding["page"] = str(finding.get("clause_reference") or "PDF")
            changed = True
        if not finding.get("section"):
            finding["section"] = str(
                finding.get("clause_reference")
                or finding.get("category")
                or ""
            )
            changed = True

    return matrix, changed


def ground_and_persist(db: Session, contract_id: Any, analysis: Any) -> None:
    """Ground a RiskAnalysis row's matrix and persist it if it changed."""
    if analysis is None:
        return
    grounded, changed = ground_risk_matrix(db, contract_id, analysis.risk_matrix)
    if changed:
        analysis.risk_matrix = grounded
        # In-place mutation of the JSON list is invisible to SQLAlchemy's
        # change tracking; flag it explicitly or the UPDATE is never issued
        # and grounding re-runs (slowly) on every request.
        try:
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(analysis, "risk_matrix")
            db.commit()
        except Exception:  # noqa: BLE001
            db.rollback()
