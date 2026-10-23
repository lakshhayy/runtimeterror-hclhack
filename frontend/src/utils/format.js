const inr = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 })

const dateFmt = new Intl.DateTimeFormat('en-IN', {
  timeZone: 'Asia/Kolkata',
  dateStyle: 'medium',
  timeStyle: 'short',
})

/** 500000 -> ₹5,00,000 */
export function formatINR(n) {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return '—'
  return inr.format(Number(n))
}

/** ISO string -> "23 Oct 2026, 2:49 pm" in IST */
export function formatDate(iso) {
  if (!iso) return '—'
  return dateFmt.format(new Date(iso))
}
