import { EvidenceItem } from '@/src/contexts/evidence-context';

/**
 * Helpers that turn agent outputs into EvidenceItems grounded in the PDF.
 * Every item carries: which agent produced it, why it matters, and the exact
 * source text (with a `highlight` pinpointed from the document).
 */

const truncate = (text: string, max = 320): string => {
  const clean = String(text || '').replace(/\s+/g, ' ').trim();
  return clean.length > max ? `${clean.slice(0, max)}…` : clean;
};

/** Pick the most relevant sentence of a passage to highlight. */
const pinpoint = (text: string, keywords: string[] = []): string => {
  const clean = String(text || '').replace(/\s+/g, ' ').trim();
  if (!clean) return '';
  const sentences = clean.match(/[^.!?]+[.!?]*/g) || [clean];
  const lowered = keywords.map((k) => k.toLowerCase());
  const hit = sentences.find((s) => lowered.some((k) => s.toLowerCase().includes(k)));
  return truncate(hit || sentences[0], 220);
};

const severityOf = (finding: Record<string, unknown>): string => {
  const raw =
    (finding.severity as string) ||
    (finding.risk_level as string) ||
    (finding.status as string) ||
    'Medium';
  return raw;
};

export function evidenceFromRiskMatrix(
  matrix: Array<Record<string, unknown>> | null | undefined,
  agentName = 'Risk Analysis',
): EvidenceItem[] {
  if (!Array.isArray(matrix)) return [];
  return matrix
    .filter((f) => f && typeof f === 'object')
    .map((f, index) => {
      const sourceText = String(f.source_text || f.description || f.issue || f.evidence || '');
      const issue = String(f.issue || f.description || f.title || f.category || 'Risk finding');
      return {
        id: `risk-${index}-${truncate(issue, 40)}`,
        agent: agentName,
        finding: truncate(issue, 90),
        severity: severityOf(f),
        explanation:
          String(f.mitigation || f.impact || f.financial_impact || f.business_impact || '') ||
          `Identified by the ${agentName} agent in the uploaded PDF.`,
        page: String(f.page || f.clause_reference || 'PDF'),
        section: String(f.section || f.clause_reference || f.category || ''),
        sourceText: sourceText || 'No verbatim passage was returned for this finding.',
        highlight: pinpoint(sourceText, ['shall', 'must', 'liable', 'terminate', 'indemnif', 'confidential']),
        matchScore: typeof f.confidence_score === 'number' ? (f.confidence_score as number) : undefined,
      } satisfies EvidenceItem;
    });
}

export function evidenceFromClauses(
  clauses: Array<Record<string, unknown>> | null | undefined,
  agentName = 'Clause Extraction',
): EvidenceItem[] {
  if (!Array.isArray(clauses)) return [];
  return clauses.slice(0, 12).map((c, index) => {
    const text = String(c.original_text || c.content || c.text || '');
    const title = String(c.clause_type || c.title || c.category || 'Clause');
    return {
      id: `clause-${index}-${truncate(title, 40)}`,
      agent: agentName,
      finding: truncate(title, 90),
      severity: 'Info',
      explanation: `Extracted verbatim by the ${agentName} agent — this clause defines rights and obligations in the document.`,
      page: 'PDF text',
      section: title,
      sourceText: truncate(text, 500) || 'No clause text captured.',
      highlight: pinpoint(text, ['shall', 'will', 'must', 'may', 'agree']),
      matchScore: typeof c.confidence_score === 'number' ? (c.confidence_score as number) : undefined,
    } satisfies EvidenceItem;
  });
}

export function evidenceFromCompliance(
  issues: Array<Record<string, unknown>> | null | undefined,
  agentName = 'Compliance',
): EvidenceItem[] {
  if (!Array.isArray(issues)) return [];
  return issues.slice(0, 10).map((issue, index) => {
    const status = String(issue.status || issue.compliance_status || 'Review');
    const clauseType = String(issue.clause_type || issue.framework || issue.issue || issue.finding || 'Compliance requirement');
    const gap = String(issue.gap_analysis || issue.description || issue.explanation || issue.requirement || issue.issue || '');
    return {
      id: `compliance-${index}-${truncate(clauseType, 40)}`,
      agent: agentName,
      finding: truncate(clauseType, 90),
      severity: /non-compliant/i.test(status) ? 'High' : /partial/i.test(status) ? 'Medium' : 'Low',
      explanation: gap
        ? truncate(gap, 280)
        : `Checked against ${String(issue.framework || 'the applicable compliance framework')} by the ${agentName} agent.`,
      page: 'PDF text',
      section: clauseType,
      sourceText: gap || 'Compliance evaluation returned no verbatim passage.',
      highlight: pinpoint(gap, ['shall', 'must', 'required', 'not']),
      matchScore: undefined,
    } satisfies EvidenceItem;
  });
}

export function evidenceFromNegotiation(
  suggestions: Array<Record<string, unknown>> | null | undefined,
  agentName = 'Negotiation',
): EvidenceItem[] {
  if (!Array.isArray(suggestions)) return [];
  return suggestions.slice(0, 10).map((s, index) => {
    const clause = String(s.clause_title || s.clause || s.title || 'Suggested redline');
    const problem = String(s.problem || s.issue || s.rationale || s.reason || s.suggestion || '');
    const wording = String(s.current_wording || s.wording || s.existing_text || problem);
    const fix = String(s.suggested_redline || s.recommended_wording || s.recommendation || s.proposed_wording || '');
    return {
      id: `negotiation-${index}-${truncate(clause, 40)}`,
      agent: agentName,
      finding: truncate(clause, 90),
      severity: String(s.priority || s.risk_level || 'Medium'),
      explanation: truncate(
        [problem && `Problem: ${problem}`, fix && `Proposed: ${fix}`].filter(Boolean).join(' ') ||
          `Redline proposed by the ${agentName} agent.`,
        280,
      ),
      page: 'PDF text',
      section: clause,
      sourceText: truncate(wording, 500) || 'Clause wording not returned.',
      highlight: pinpoint(wording, ['shall', 'must', 'may', 'not', 'terminat']),
      matchScore: undefined,
    } satisfies EvidenceItem;
  });
}

export function evidenceFromChatSources(
  sources: Array<{ chunk_id?: string; parent_text?: string; child_text?: string; relevance_score?: number }> | null | undefined,
  agentName = 'Retrieval / Chat',
): EvidenceItem[] {
  if (!Array.isArray(sources)) return [];
  return sources.map((s, index) => {
    const text = String(s.parent_text || s.child_text || '');
    return {
      id: s.chunk_id || `source-${index}`,
      agent: agentName,
      finding: 'Retrieved passage',
      severity: 'Info',
      explanation: 'Highest-scoring passage retrieved from the PDF for this question.',
      page: 'PDF passage',
      section: 'Retrieval',
      sourceText: truncate(text, 500) || 'No text available',
      highlight: truncate(text, 160),
      matchScore: s.relevance_score,
    } satisfies EvidenceItem;
  });
}

export function evidenceFromKnowledgeGraph(
  entities: Array<Record<string, unknown>> | null | undefined,
  agentName = 'Knowledge Graph',
): EvidenceItem[] {
  if (!Array.isArray(entities)) return [];
  return entities.slice(0, 8).map((e, index) => {
    const name = String(e.name || e.label || e.id || 'Entity');
    const desc = String(e.description || e.type || '');
    return {
      id: `kg-${index}-${truncate(name, 40)}`,
      agent: agentName,
      finding: truncate(name, 90),
      severity: 'Info',
      explanation: desc
        ? `Entity resolved by the ${agentName} agent: ${truncate(desc, 200)}`
        : `Entity identified by the ${agentName} agent.`,
      page: 'PDF text',
      section: String(e.type || 'Entity'),
      sourceText: truncate(desc || name, 400),
      highlight: truncate(name, 120),
      matchScore: undefined,
    } satisfies EvidenceItem;
  });
}
