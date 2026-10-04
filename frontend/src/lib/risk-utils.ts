// Risk score semantics: overall_score is 0-100 where HIGHER = RISKIER.
// (See backend risk prompt contract: "overall_score": 75 with High severity findings.)

export type RiskLevel = 'High' | 'Medium' | 'Low';

export const HIGH_RISK_MIN = 70;
export const MEDIUM_RISK_MIN = 40;

export function riskLevel(score: number | null | undefined): RiskLevel {
  const s = score ?? 0;
  if (s >= HIGH_RISK_MIN) return 'High';
  if (s >= MEDIUM_RISK_MIN) return 'Medium';
  return 'Low';
}

export const riskBadgeClass = (level: RiskLevel): string =>
  level === 'High'
    ? 'bg-rose-50 text-rose-700 border-rose-200'
    : level === 'Medium'
      ? 'bg-amber-50 text-amber-700 border-amber-200'
      : 'bg-emerald-50 text-emerald-700 border-emerald-200';

export const riskDotClass = (level: RiskLevel): string =>
  level === 'High' ? 'bg-rose-500' : level === 'Medium' ? 'bg-amber-500' : 'bg-emerald-500';
