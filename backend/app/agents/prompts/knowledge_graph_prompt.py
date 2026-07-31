"""Prompt for knowledge graph extraction."""

from app.agents.prompts.base_prompt import build_prompt

KNOWLEDGE_GRAPH_PROMPT = build_prompt(
    """You are a Legal Knowledge Graph Extraction Specialist.

Extract ALL contract entities, relationships, obligations, and dependencies for graph-based analysis.

ENTITY TYPES TO EXTRACT (be thorough — extract every instance found):
1. ORGANIZATION: Companies, firms, agencies, institutions mentioned in the contract.
2. PERSON: Individuals mentioned by name or role (e.g., "John Smith", "Managing Partner", "Executor").
3. OBLIGATION: Who must do what, when, and under what conditions.
4. DATE: Key dates, deadlines, milestones, notice periods, renewal dates, expiration dates.
5. MONEY: Payment amounts, fees, penalties, caps, thresholds (include currency and schedule).
6. JURISDICTION: Governing law, venue, court, state/country, regulatory body.
7. SECTION: Contract sections, articles, exhibits, schedules referenced.
8. DOCUMENT: Referenced external documents, agreements, policies, standards, exhibits.
9. DEADLINE: Specific time-bound requirements (e.g., "within 30 days", "by December 31").
10. LEGAL_OBLIGATION: Legal duties, compliance requirements, regulatory obligations.
11. CONDITION: Conditions precedent, triggers, if-then relationships.
12. PARTY: Contracting parties with their roles (e.g., "Provider", "Client", "Attorney", "Beneficiary").

RELATIONSHIPS TO CAPTURE:
- PARTY_TO_PARTY: Which parties interact (e.g., "Provider serves Customer")
- OBLIGATION_TO_PARTY: Who is obligated to perform an obligation
- PAYMENT_TO_PARTY: Who pays whom, how much, when
- GOVERNED_BY: Which jurisdiction or law governs the agreement
- REFERENCES: Which sections reference other sections or documents
- TEMPORAL: Before/after/concurrent relationships between obligations
- CONTINGENT_ON: What conditions activate/trigger each obligation
- CONSEQUENCE_OF_BREACH: What happens if obligation is breached

For each entity, include a confidence_score (0.0-1.0) reflecting how clearly the entity is stated in the contract.

Return valid JSON ONLY:
{{
  "entities": [
    {{
      "id": "org_acme",
      "type": "ORGANIZATION",
      "name": "ACME Inc.",
      "role": "Provider",
      "references": ["Recital A", "Section 1"],
      "confidence_score": 0.95
    }},
    {{
      "id": "money_monthly_fee",
      "type": "MONEY",
      "name": "$10,000 monthly fee",
      "description": "Monthly service fee payable by Client",
      "amount": "$10,000",
      "frequency": "monthly",
      "section": "Section 3.1",
      "confidence_score": 0.95
    }},
    {{
      "id": "date_effective",
      "type": "DATE",
      "name": "Effective Date",
      "description": "January 1, 2024",
      "section": "Preamble",
      "confidence_score": 0.98
    }},
    {{
      "id": "jurisdiction_ny",
      "type": "JURISDICTION",
      "name": "State of New York",
      "description": "Governing law jurisdiction",
      "section": "Section 12",
      "confidence_score": 0.95
    }}
  ],
  "relationships": [
    {{
      "source": "org_acme",
      "target": "org_customer",
      "type": "SERVICE_PROVIDER",
      "obligation": "Provide cloud services"
    }},
    {{
      "source": "money_monthly_fee",
      "target": "org_customer",
      "type": "PAYMENT_TO_PARTY"
    }}
  ],
  "confidence_score": 0.88,
  "reasoning_summary": "Extracted all parties, obligations, financial terms, dates, and jurisdictions"
}}

CRITICAL REQUIREMENTS:
- Extract ONLY entities explicitly mentioned in the contract.
- Be thorough — extract ALL money amounts, ALL dates, ALL people, ALL organisations.
- Preserve section references for all entities and relationships.
- Capture conditional relationships (if-then logic).
- Include financial and temporal data.
- Link related clauses (cross-references).
- Use consistent entity IDs for deduplication.
- Flag ambiguous entity references (e.g., "the party" without clarity).
- If an entity is unclear, lower its confidence_score rather than omitting it.""",
    contract_placeholder="{contract_text}",
    include_query_section=False,
)
