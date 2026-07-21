/**
 * Director Portal — Design Tokens & Global Styles
 * Premium dark-mode judicial/professional palette
 */

export const colors = {
  // Primary
  navy: '#0f172a',
  navyLight: '#1e293b',
  navyMid: '#334155',
  slate: '#64748b',
  slateLight: '#94a3b8',
  white: '#f8fafc',
  offWhite: '#f1f5f9',

  // Severity
  critical: '#dc2626',
  criticalBg: '#fef2f2',
  criticalBorder: '#fca5a5',
  high: '#ea580c',
  highBg: '#fff7ed',
  highBorder: '#fdba74',
  moderate: '#d97706',
  moderateBg: '#fffbeb',
  moderateBorder: '#fcd34d',
  low: '#16a34a',
  lowBg: '#f0fdf4',
  lowBorder: '#86efac',

  // Status
  submitted: '#2563eb',
  underReview: '#7c3aed',
  changesRequested: '#d97706',
  approved: '#16a34a',
  guardianPending: '#0891b2',

  // Diff / redline
  added: '#16a34a',
  addedBg: '#dcfce7',
  removed: '#dc2626',
  removedBg: '#fee2e2',

  // UI
  border: '#e2e8f0',
  borderDark: '#cbd5e1',
  surface: '#ffffff',
  surfaceElevated: '#f8fafc',
  accent: '#2563eb',
  accentLight: '#dbeafe',
  shadow: 'rgba(15, 23, 42, 0.08)',
};

export const severity = {
  critical: { color: colors.critical, bg: colors.criticalBg, border: colors.criticalBorder, label: 'CRITICAL' },
  high: { color: colors.high, bg: colors.highBg, border: colors.highBorder, label: 'HIGH' },
  moderate: { color: colors.moderate, bg: colors.moderateBg, border: colors.moderateBorder, label: 'MODERATE' },
  low: { color: colors.low, bg: colors.lowBg, border: colors.lowBorder, label: 'LOW' },
};

export const statusMeta: Record<string, { color: string; label: string }> = {
  submitted: { color: colors.submitted, label: 'Submitted' },
  under_review: { color: colors.underReview, label: 'Under Review' },
  changes_requested: { color: colors.changesRequested, label: 'Changes Requested' },
  approved: { color: colors.approved, label: 'Approved' },
  guardian_ack_pending: { color: colors.guardianPending, label: 'Guardian Ack. Pending' },
  acknowledged: { color: colors.low, label: 'Acknowledged' },
  ack_unreachable: { color: colors.slate, label: 'Unreachable' },
  closed: { color: colors.slate, label: 'Closed' },
};

export const typography = {
  fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
  sizes: { xs: 11, sm: 13, md: 15, lg: 17, xl: 21, xxl: 27, hero: 36 },
  weights: { regular: '400', medium: '500', semibold: '600', bold: '700' },
};

export const spacing = {
  xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32, xxxl: 48,
};

export const radius = {
  sm: 6, md: 10, lg: 14, xl: 20, pill: 999,
};

export const shadows = {
  sm: '0 1px 3px rgba(15,23,42,0.06), 0 1px 2px rgba(15,23,42,0.04)',
  md: '0 4px 12px rgba(15,23,42,0.08), 0 2px 4px rgba(15,23,42,0.04)',
  lg: '0 10px 30px rgba(15,23,42,0.12), 0 4px 8px rgba(15,23,42,0.06)',
};
