import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { Calculator, Search } from 'lucide-react'
import client, { getErrorMessage } from '../api/client'
import Badge from '../components/Badge'
import Button from '../components/Button'
import Card from '../components/Card'
import EmptyState from '../components/EmptyState'
import InfoTip from '../components/InfoTip'
import PageHeader from '../components/PageHeader'
import Spinner from '../components/Spinner'
import { formatINR } from '../utils/format'

const TYPES = [
  { value: '', label: 'All' },
  { value: 'PERSONAL', label: 'Personal' },
  { value: 'HOME', label: 'Home' },
  { value: 'VEHICLE', label: 'Vehicle' },
  { value: 'EDUCATION', label: 'Education' },
]

const TYPE_LABELS = { PERSONAL: 'Personal', HOME: 'Home', VEHICLE: 'Vehicle', EDUCATION: 'Education' }
const SEGMENT_LABELS = { SALARIED: 'Salaried', SELF_EMPLOYED: 'Self-employed', STUDENT: 'Student' }

function years(months) {
  const y = months / 12
  return Number.isInteger(y) ? `${y}` : y.toFixed(1)
}

function tenureText(p) {
  return `${p.tenureMin}–${p.tenureMax} months (${years(p.tenureMin)}–${years(p.tenureMax)} yrs)`
}

function segmentsText(segments) {
  if (!segments.length) return 'All customers'
  return segments.map((s) => SEGMENT_LABELS[s] || s).join(', ')
}

function ProductCard({ product: p }) {
  const navigate = useNavigate()
  const emiAmount = Math.min(p.amountMin * 5, p.amountMax)

  return (
    <Card className="flex flex-col">
      <div className="mb-3 flex items-start justify-between gap-2">
        <div>
          <h3 className="font-semibold leading-snug">{p.name}</h3>
          <p className="text-xs text-slate-400">{p.id}</p>
        </div>
        <Badge variant="info">{TYPE_LABELS[p.loanType]}</Badge>
      </div>
      <p className="mb-4 text-sm text-slate-600">{p.description}</p>

      <dl className="mb-5 space-y-2 text-sm">
        <div className="flex justify-between gap-3">
          <dt className="text-slate-500">Interest</dt>
          <dd className="text-right font-medium text-navy">
            {p.rateMin.toFixed(1)}%–{p.rateMax.toFixed(1)}% p.a.
          </dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-slate-500">Tenure</dt>
          <dd className="text-right font-medium text-navy">{tenureText(p)}</dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-slate-500">Amount</dt>
          <dd className="text-right font-medium text-navy">
            {formatINR(p.amountMin)} – {formatINR(p.amountMax)}
          </dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="flex items-center gap-1 text-slate-500">
            Processing fee
            <InfoTip text="A one-time fee charged on the loan amount when the loan is disbursed." />
          </dt>
          <dd className="text-right font-medium text-navy">
            {p.processingFeePct === 0 ? 'Nil' : `${p.processingFeePct}%`}
          </dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-slate-500">For</dt>
          <dd className="text-right font-medium text-navy">{segmentsText(p.eligibleSegments)}</dd>
        </div>
      </dl>

      <div className="mt-auto flex gap-2">
        <Button
          variant="secondary"
          className="flex-1"
          onClick={() =>
            navigate(`/emi?amount=${emiAmount}&rate=${p.rateMin}&tenure=${p.tenureMax}&productId=${p.id}`)
          }
        >
          <Calculator className="h-4 w-4" /> Calculate EMI
        </Button>
        <Button className="flex-1" onClick={() => navigate(`/apply?productId=${p.id}`)}>
          Apply
        </Button>
      </div>
    </Card>
  )
}

export default function Products() {
  const [type, setType] = useState('')
  const [search, setSearch] = useState('')
  const [query, setQuery] = useState('') // debounced search
  const [sort, setSort] = useState('rate_asc')
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [reload, setReload] = useState(0)

  // Debounce typing by 300ms.
  useEffect(() => {
    const t = setTimeout(() => setQuery(search.trim()), 300)
    return () => clearTimeout(t)
  }, [search])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    const params = { sort }
    if (type) params.type = type
    if (query) params.q = query
    client
      .get('/products', { params })
      .then((res) => {
        if (cancelled) return
        setProducts(res.data)
        setError(false)
      })
      .catch((err) => {
        if (cancelled) return
        setError(true)
        toast.error(getErrorMessage(err))
      })
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [type, query, sort, reload])

  function clearFilters() {
    setType('')
    setSearch('')
    setQuery('')
    setReload((n) => n + 1)
  }

  return (
    <div>
      <PageHeader title="Loan Products" subtitle="Compare Kestrel Bank loans and estimate your EMI" />

      <div className="mb-6 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex flex-wrap gap-2">
          {TYPES.map((t) => (
            <button
              key={t.value}
              onClick={() => setType(t.value)}
              className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
                type === t.value ? 'bg-navy text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
        <div className="flex flex-col gap-2 sm:flex-row">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search e.g. used car, abroad"
              className="w-full rounded-lg border border-slate-300 py-2 pl-9 pr-3 text-sm outline-none focus:border-teal focus:ring-2 focus:ring-teal/20 sm:w-64"
            />
          </div>
          <select
            value={sort}
            onChange={(e) => setSort(e.target.value)}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-teal"
            aria-label="Sort products"
          >
            <option value="rate_asc">Lowest interest first</option>
            <option value="rate_desc">Highest interest first</option>
            <option value="amount_desc">Highest loan amount first</option>
          </select>
        </div>
      </div>

      {loading ? (
        <div className="py-16">
          <Spinner label="Loading products…" />
        </div>
      ) : error ? (
        <EmptyState
          title="Couldn't load products"
          message="Please check your connection and try again."
          action={<Button onClick={() => setReload((n) => n + 1)}>Retry</Button>}
        />
      ) : products.length === 0 ? (
        <EmptyState
          title="No products match"
          message="Try a different search or loan type."
          action={
            <Button variant="secondary" onClick={clearFilters}>
              Clear filters
            </Button>
          }
        />
      ) : (
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {products.map((p) => (
            <ProductCard key={p.id} product={p} />
          ))}
        </div>
      )}
    </div>
  )
}
