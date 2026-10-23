// Badge colours: success = OK, warning = attention, danger = blocked.

export const STATUS_LABELS = {
  DRAFT: 'Draft',
  SUBMITTED: 'Submitted',
  UNDER_VERIFICATION: 'Under verification',
  UNDER_REVIEW: 'Under review',
  APPROVED: 'Approved',
  REJECTED: 'Rejected',
  DISBURSED: 'Disbursed',
}

const STATUS_VARIANTS = {
  DRAFT: 'neutral',
  SUBMITTED: 'info',
  UNDER_VERIFICATION: 'warning',
  UNDER_REVIEW: 'info',
  APPROVED: 'success',
  REJECTED: 'danger',
  DISBURSED: 'success',
}

export function statusVariant(status) {
  return STATUS_VARIANTS[status] || 'neutral'
}

export function riskVariant(band) {
  return { LOW: 'success', MEDIUM: 'warning', HIGH: 'danger' }[band] || 'neutral'
}

export function eligibilityVariant(indicator) {
  return { LIKELY_ELIGIBLE: 'success', BORDERLINE: 'warning', UNLIKELY: 'danger' }[indicator] || 'neutral'
}

export const ELIGIBILITY_LABELS = {
  LIKELY_ELIGIBLE: 'Likely eligible',
  BORDERLINE: 'Borderline',
  UNLIKELY: 'Unlikely',
}

const RECOMMENDATION_LABELS = {
  RECOMMEND_APPROVE: 'Recommend approve',
  RECOMMEND_REJECT: 'Recommend reject',
  MANUAL_REVIEW: 'Manual review',
  REQUEST_ADDITIONAL_DOCUMENTS: 'Request documents',
}

export function recommendationLabel(rec) {
  return RECOMMENDATION_LABELS[rec] || rec || '—'
}

export const DOC_LABELS = {
  IDENTITY: 'Identity proof',
  ADDRESS: 'Address proof',
  INCOME: 'Income proof',
}

const ROLE_HOME = {
  CUSTOMER: '/advisor',
  OFFICER: '/officer/applications',
  ANALYST: '/analyst/queue',
}

/** Landing page for each role. */
export function roleHome(role) {
  return ROLE_HOME[role] || '/login'
}
