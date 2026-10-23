import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import { AlertTriangle, Check } from 'lucide-react'
import client, { getErrorMessage } from '../api/client'
import Button from '../components/Button'
import Card from '../components/Card'
import DocumentUploadRow from '../components/DocumentUploadRow'
import EmptyState from '../components/EmptyState'
import PageHeader from '../components/PageHeader'
import Spinner from '../components/Spinner'
import { useAuth } from '../context/AuthContext'
import { formatINR } from '../utils/format'
import { DOC_LABELS } from '../utils/labels'

const DOC_TYPES = ['IDENTITY', 'ADDRESS', 'INCOME']
const STEPS = ['Loan details', 'Documents', 'Review & submit']

const inputClass =
  'w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-teal focus:ring-2 focus:ring-teal/20 disabled:bg-slate-50 disabled:text-slate-500'

function StepIndicator({ current }) {
  return (
    <ol className="mb-6 flex items-center gap-2 text-sm">
      {STEPS.map((label, i) => {
        const done = i < current
        const active = i === current
        return (
          <li key={label} className="flex flex-1 items-center gap-2">
            <span
              className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${
                done ? 'bg-teal text-white' : active ? 'bg-navy text-white' : 'bg-slate-200 text-slate-500'
              }`}
            >
              {done ? <Check className="h-4 w-4" /> : i + 1}
            </span>
            <span className={`hidden sm:inline ${active ? 'font-semibold text-navy' : 'text-slate-500'}`}>{label}</span>
            {i < STEPS.length - 1 && <span className="h-px flex-1 bg-slate-200" />}
          </li>
        )
      })}
    </ol>
  )
}

function validate(form, product) {
  if (!product) return 'Please choose a loan product.'
  const amount = Number(form.amount)
  const tenure = Number(form.tenure)
  if (!(amount >= product.amountMin && amount <= product.amountMax)) {
    return `Amount must be between ${formatINR(product.amountMin)} and ${formatINR(product.amountMax)} for this product.`
  }
  if (!(Number.isInteger(tenure) && tenure >= product.tenureMin && tenure <= product.tenureMax)) {
    return `Tenure must be between ${product.tenureMin} and ${product.tenureMax} months for this product.`
  }
  if (!(Number(form.income) > 0)) return 'Please enter your monthly income.'
  return null
}

export default function Apply() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [params] = useSearchParams()

  const [products, setProducts] = useState([])
  const [loadingProducts, setLoadingProducts] = useState(true)
  const [loadError, setLoadError] = useState(false)
  const [form, setForm] = useState({
    productId: params.get('productId') || '',
    amount: params.get('amount') || '',
    tenure: params.get('tenure') || '',
    income: user?.monthlyIncome ?? '',
    purpose: '',
  })
  const [emi, setEmi] = useState(null)
  const [saving, setSaving] = useState(false)
  const [application, setApplication] = useState(null)
  const [documents, setDocuments] = useState({})
  const [submitting, setSubmitting] = useState(false)

  const product = products.find((p) => p.id === form.productId)
  const formError = validate(form, product)
  const step = !application ? 0 : Object.keys(documents).length === 0 ? 1 : 2
  const missing = DOC_TYPES.filter((t) => !documents[t])

  useEffect(() => {
    client
      .get('/products')
      .then((res) => {
        setProducts(res.data)
        // Coming from a product card with only ?productId: fill sensible defaults.
        setForm((f) => {
          const p = res.data.find((x) => x.id === f.productId)
          if (!p) return f
          return {
            ...f,
            amount: f.amount || String(Math.min(p.amountMin * 5, p.amountMax)),
            tenure: f.tenure || String(p.tenureMax),
          }
        })
      })
      .catch((err) => {
        setLoadError(true)
        toast.error(getErrorMessage(err))
      })
      .finally(() => setLoadingProducts(false))
  }, [])

  // Live indicative EMI at the product's starting rate.
  useEffect(() => {
    if (formError || !product) return
    let cancelled = false
    const t = setTimeout(() => {
      client
        .post('/emi/calculate', { principal: Number(form.amount), annualRate: product.rateMin, tenureMonths: Number(form.tenure) })
        .then((res) => !cancelled && setEmi(res.data.emi))
        .catch(() => !cancelled && setEmi(null))
    }, 300)
    return () => {
      cancelled = true
      clearTimeout(t)
    }
  }, [form.amount, form.tenure, product, formError])

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }))
  }

  function chooseProduct(id) {
    const p = products.find((x) => x.id === id)
    setForm((f) => ({
      ...f,
      productId: id,
      amount: f.amount || (p ? String(Math.min(p.amountMin * 5, p.amountMax)) : ''),
      tenure: f.tenure || (p ? String(p.tenureMax) : ''),
    }))
  }

  async function saveDraft() {
    if (formError) {
      toast.error(formError)
      return
    }
    setSaving(true)
    try {
      const res = await client.post('/applications', {
        productId: form.productId,
        amount: Number(form.amount),
        tenureMonths: Number(form.tenure),
        declaredIncome: Number(form.income),
        purpose: form.purpose,
      })
      setApplication(res.data)
      toast.success('Draft saved ✓')
    } catch (err) {
      toast.error(getErrorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  async function submit() {
    setSubmitting(true)
    try {
      await client.post(`/applications/${application.id}/submit`)
      toast.success('Application submitted')
      navigate(`/applications/${application.id}`)
    } catch (err) {
      toast.error(getErrorMessage(err))
      setSubmitting(false)
    }
  }

  if (loadingProducts) {
    return (
      <div className="py-20">
        <Spinner label="Loading…" />
      </div>
    )
  }
  if (loadError) {
    return (
      <EmptyState
        title="Couldn't load loan products"
        message="Please refresh the page to try again."
        action={<Button onClick={() => window.location.reload()}>Refresh</Button>}
      />
    )
  }

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader title="Apply for a Loan" subtitle="Three quick steps: loan details, documents, then submit" />
      <StepIndicator current={step} />

      <Card className="mb-6">
        <h2 className="mb-4 text-lg font-semibold">1. Loan details</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="sm:col-span-2">
            <label htmlFor="product" className="mb-1 block text-sm font-medium text-navy">
              Loan product
            </label>
            <select
              id="product"
              value={form.productId}
              disabled={Boolean(application)}
              onChange={(e) => chooseProduct(e.target.value)}
              className={inputClass}
            >
              <option value="">Choose a product…</option>
              {products.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.id}) · from {p.rateMin}% p.a.
                </option>
              ))}
            </select>
            {product && (
              <p className="mt-1 text-xs text-slate-500">
                Allowed: {formatINR(product.amountMin)} – {formatINR(product.amountMax)} · {product.tenureMin}–
                {product.tenureMax} months
              </p>
            )}
          </div>
          <div>
            <label htmlFor="amount" className="mb-1 block text-sm font-medium text-navy">
              Amount (₹)
            </label>
            <input
              id="amount"
              type="number"
              value={form.amount}
              disabled={Boolean(application)}
              onChange={(e) => update('amount', e.target.value)}
              className={inputClass}
            />
          </div>
          <div>
            <label htmlFor="tenure" className="mb-1 block text-sm font-medium text-navy">
              Tenure (months)
            </label>
            <input
              id="tenure"
              type="number"
              value={form.tenure}
              disabled={Boolean(application)}
              onChange={(e) => update('tenure', e.target.value)}
              className={inputClass}
            />
          </div>
          <div>
            <label htmlFor="income" className="mb-1 block text-sm font-medium text-navy">
              Monthly income (₹)
            </label>
            <input
              id="income"
              type="number"
              value={form.income}
              disabled={Boolean(application)}
              onChange={(e) => update('income', e.target.value)}
              className={inputClass}
            />
          </div>
          <div>
            <label htmlFor="purpose" className="mb-1 block text-sm font-medium text-navy">
              Purpose
            </label>
            <input
              id="purpose"
              value={form.purpose}
              maxLength={300}
              disabled={Boolean(application)}
              onChange={(e) => update('purpose', e.target.value)}
              placeholder="e.g. Buying a used car"
              className={inputClass}
            />
          </div>
        </div>

        <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="text-sm">
            {formError ? (
              <span className="text-red-600">{formError}</span>
            ) : emi !== null ? (
              <span className="text-slate-600">
                Indicative EMI: <span className="text-lg font-bold text-navy">{formatINR(emi)}</span>/month at{' '}
                {product.rateMin}% p.a.
              </span>
            ) : null}
          </div>
          {application ? (
            <span className="flex items-center gap-1 text-sm font-medium text-emerald-700">
              <Check className="h-4 w-4" /> Draft saved · {application.applicationId}
            </span>
          ) : (
            <Button onClick={saveDraft} loading={saving} disabled={Boolean(formError)}>
              Save draft
            </Button>
          )}
        </div>
      </Card>

      <Card className={`mb-6 ${application ? '' : 'pointer-events-none opacity-50'}`}>
        <h2 className="mb-1 text-lg font-semibold">2. Documents</h2>
        <p className="mb-4 text-sm text-slate-500">PDF, JPG or PNG, up to 5 MB each.</p>
        <div className="space-y-3">
          {DOC_TYPES.map((t) => (
            <DocumentUploadRow
              key={t}
              appId={application?.id}
              docType={t}
              label={DOC_LABELS[t]}
              uploaded={documents[t]}
              onUploaded={(doc) => setDocuments((d) => ({ ...d, [t]: doc }))}
            />
          ))}
        </div>
      </Card>

      <Card className={application ? '' : 'pointer-events-none opacity-50'}>
        <h2 className="mb-4 text-lg font-semibold">3. Review & submit</h2>
        {product && (
          <dl className="grid gap-2 text-sm sm:grid-cols-2">
            <div className="flex justify-between sm:block">
              <dt className="text-slate-500">Product</dt>
              <dd className="font-medium text-navy">{product.name}</dd>
            </div>
            <div className="flex justify-between sm:block">
              <dt className="text-slate-500">Amount</dt>
              <dd className="font-medium text-navy">{formatINR(Number(form.amount))}</dd>
            </div>
            <div className="flex justify-between sm:block">
              <dt className="text-slate-500">Tenure</dt>
              <dd className="font-medium text-navy">{form.tenure} months</dd>
            </div>
            <div className="flex justify-between sm:block">
              <dt className="text-slate-500">Indicative EMI</dt>
              <dd className="font-medium text-navy">{emi !== null ? formatINR(emi) : '—'}</dd>
            </div>
            <div className="flex justify-between sm:col-span-2 sm:block">
              <dt className="text-slate-500">Documents</dt>
              <dd className="font-medium text-navy">
                {DOC_TYPES.filter((t) => documents[t]).map((t) => DOC_LABELS[t]).join(', ') || 'None uploaded yet'}
              </dd>
            </div>
          </dl>
        )}
        {missing.length > 0 && (
          <div className="mt-4 space-y-1">
            {missing.map((t) => (
              <p key={t} className="flex items-center gap-2 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800">
                <AlertTriangle className="h-4 w-4 shrink-0" /> {DOC_LABELS[t]} is missing — our checks will flag it.
              </p>
            ))}
          </div>
        )}
        <Button className="mt-5 w-full" onClick={submit} loading={submitting} disabled={!application}>
          {submitting ? 'AI agents are checking your application…' : 'Submit application'}
        </Button>
        {submitting && (
          <p className="mt-2 text-center text-xs text-slate-500">
            Document, credit and compliance checks usually take 10–15 seconds.
          </p>
        )}
      </Card>
    </div>
  )
}
