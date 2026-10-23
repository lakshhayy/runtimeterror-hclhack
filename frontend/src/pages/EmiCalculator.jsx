import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import { ChevronDown, ChevronUp, Lightbulb } from 'lucide-react'
import client, { getErrorMessage } from '../api/client'
import Badge from '../components/Badge'
import Button from '../components/Button'
import Card from '../components/Card'
import InfoTip from '../components/InfoTip'
import PageHeader from '../components/PageHeader'
import Spinner from '../components/Spinner'
import { useAuth } from '../context/AuthContext'
import { formatINR } from '../utils/format'
import { ELIGIBILITY_LABELS, eligibilityVariant } from '../utils/labels'

// Slider limits when no product is selected (match the API's validation).
const DEFAULT_LIMITS = { amountMin: 10000, amountMax: 10000000, rateMin: 0, rateMax: 36, tenureMin: 1, tenureMax: 480 }

function numberParam(params, key, fallback) {
  const n = Number(params.get(key))
  return params.get(key) && Number.isFinite(n) ? n : fallback
}

function validate(amount, rate, tenure, limits) {
  if (!(amount >= limits.amountMin && amount <= limits.amountMax)) {
    return `Amount must be between ${formatINR(limits.amountMin)} and ${formatINR(limits.amountMax)}.`
  }
  if (!(rate >= limits.rateMin && rate <= limits.rateMax)) {
    return `Interest rate must be between ${limits.rateMin}% and ${limits.rateMax}%.`
  }
  if (!(Number.isInteger(tenure) && tenure >= limits.tenureMin && tenure <= limits.tenureMax)) {
    return `Tenure must be a whole number of months between ${limits.tenureMin} and ${limits.tenureMax}.`
  }
  return null
}

function SliderField({ id, label, value, onChange, min, max, step, display }) {
  return (
    <div>
      <div className="mb-1 flex items-center justify-between gap-3">
        <label htmlFor={id} className="text-sm font-medium text-navy">
          {label}
        </label>
        <input
          id={id}
          type="number"
          value={Number.isNaN(value) ? '' : value}
          min={min}
          max={max}
          step={step}
          onChange={(e) => onChange(e.target.value === '' ? NaN : Number(e.target.value))}
          className="w-36 rounded-lg border border-slate-300 px-3 py-1.5 text-right text-sm outline-none focus:border-teal focus:ring-2 focus:ring-teal/20"
        />
      </div>
      <input
        type="range"
        aria-label={label}
        value={Number.isNaN(value) ? min : Math.min(Math.max(value, min), max)}
        min={min}
        max={max}
        step={step}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-teal"
      />
      <div className="flex justify-between text-xs text-slate-400">
        <span>{display(min)}</span>
        <span>{display(max)}</span>
      </div>
    </div>
  )
}

export default function EmiCalculator() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const productId = params.get('productId') || ''

  const [amount, setAmount] = useState(() => numberParam(params, 'amount', 500000))
  const [rate, setRate] = useState(() => numberParam(params, 'rate', 11))
  const [tenure, setTenure] = useState(() => numberParam(params, 'tenure', 60))
  const [income, setIncome] = useState(user?.monthlyIncome ?? NaN)
  const [existingEmi, setExistingEmi] = useState(user?.existingEmi ?? 0)

  const [product, setProduct] = useState(null)
  const [result, setResult] = useState(null)
  const [calcLoading, setCalcLoading] = useState(true)
  const [whatIf, setWhatIf] = useState(null)
  const [whatIfLoading, setWhatIfLoading] = useState(false)
  const [showSchedule, setShowSchedule] = useState(false)

  const limits = product
    ? {
        amountMin: product.amountMin,
        amountMax: product.amountMax,
        rateMin: product.rateMin,
        rateMax: product.rateMax,
        tenureMin: product.tenureMin,
        tenureMax: product.tenureMax,
      }
    : DEFAULT_LIMITS
  const inputError = validate(amount, rate, tenure, limits)
  const incomeError = !(income > 0) ? 'Enter your monthly income to check eligibility.' : !(existingEmi >= 0) ? 'Existing EMI cannot be negative.' : null

  // Load the product (for its allowed ranges) when we came from a product card or the advisor.
  useEffect(() => {
    if (!productId) return
    client
      .get(`/products/${productId}`)
      .then((res) => setProduct(res.data))
      .catch((err) => toast.error(getErrorMessage(err)))
  }, [productId])

  // Live EMI, 300ms after the last change.
  useEffect(() => {
    if (inputError) return
    let cancelled = false
    setCalcLoading(true)
    const t = setTimeout(() => {
      client
        .post('/emi/calculate', { principal: amount, annualRate: rate, tenureMonths: tenure })
        .then((res) => !cancelled && setResult(res.data))
        .catch((err) => !cancelled && toast.error(getErrorMessage(err)))
        .finally(() => !cancelled && setCalcLoading(false))
    }, 300)
    return () => {
      cancelled = true
      clearTimeout(t)
    }
  }, [amount, rate, tenure, inputError])

  // What-if coach, also debounced.
  useEffect(() => {
    if (inputError || incomeError) return
    let cancelled = false
    setWhatIfLoading(true)
    const body = {
      principal: amount,
      annualRate: rate,
      tenureMonths: tenure,
      monthlyIncome: income,
      existingEmi,
      tenureMin: limits.tenureMin,
      tenureMax: limits.tenureMax,
    }
    const t = setTimeout(() => {
      client
        .post('/emi/what-if', body)
        .then((res) => !cancelled && setWhatIf(res.data))
        .catch((err) => !cancelled && toast.error(getErrorMessage(err)))
        .finally(() => !cancelled && setWhatIfLoading(false))
    }, 300)
    return () => {
      cancelled = true
      clearTimeout(t)
    }
  }, [amount, rate, tenure, income, existingEmi, inputError, incomeError, limits.tenureMin, limits.tenureMax])

  function applyOption(option) {
    setTenure(option.tenureMonths)
    setAmount(option.principal)
    toast.success('Applied suggestion')
  }

  function goApply() {
    const q = new URLSearchParams({ amount: String(amount), tenure: String(tenure) })
    if (productId) q.set('productId', productId)
    navigate(`/apply?${q.toString()}`)
  }

  const principalPct = result ? Math.round((amount / result.totalPayment) * 100) : 0

  return (
    <div>
      <PageHeader
        title="EMI Calculator"
        subtitle={product ? `For ${product.name} (${product.id})` : 'See your monthly payment and repayment schedule'}
      />

      <div className="grid gap-6 lg:grid-cols-5">
        <Card className="space-y-6 lg:col-span-3">
          <SliderField
            id="amount"
            label="Loan amount (₹)"
            value={amount}
            onChange={setAmount}
            min={limits.amountMin}
            max={limits.amountMax}
            step={10000}
            display={formatINR}
          />
          <SliderField
            id="rate"
            label="Interest rate (% p.a.)"
            value={rate}
            onChange={setRate}
            min={limits.rateMin}
            max={limits.rateMax}
            step={0.05}
            display={(v) => `${v}%`}
          />
          <SliderField
            id="tenure"
            label="Tenure (months)"
            value={tenure}
            onChange={setTenure}
            min={limits.tenureMin}
            max={limits.tenureMax}
            step={1}
            display={(v) => `${v} mo`}
          />
          {inputError && <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{inputError}</p>}
        </Card>

        <Card className="flex flex-col lg:col-span-2">
          <p className="text-sm text-slate-500">Your monthly EMI</p>
          {inputError ? (
            <p className="mt-2 text-sm text-slate-500">Fix the highlighted input to see your EMI.</p>
          ) : !result ? (
            <div className="py-10">
              <Spinner />
            </div>
          ) : (
            <div className={calcLoading ? 'opacity-60 transition-opacity' : 'transition-opacity'}>
              <p className="mt-1 text-4xl font-bold text-navy">{formatINR(result.emi)}</p>
              <p className="text-xs text-slate-400">
                for {tenure} months ({(tenure / 12).toFixed(1)} years)
              </p>
              <dl className="mt-5 space-y-2 text-sm">
                <div className="flex justify-between">
                  <dt className="text-slate-500">Principal</dt>
                  <dd className="font-medium text-navy">{formatINR(amount)}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-500">Total interest</dt>
                  <dd className="font-medium text-navy">{formatINR(result.totalInterest)}</dd>
                </div>
                <div className="flex justify-between border-t border-slate-200 pt-2">
                  <dt className="text-slate-500">Total payment</dt>
                  <dd className="font-semibold text-navy">{formatINR(result.totalPayment)}</dd>
                </div>
              </dl>
              <div className="mt-5">
                <div className="flex h-3 overflow-hidden rounded-full bg-amber-400">
                  <div className="bg-teal" style={{ width: `${principalPct}%` }} />
                </div>
                <div className="mt-2 flex justify-between text-xs text-slate-500">
                  <span className="flex items-center gap-1">
                    <span className="h-2 w-2 rounded-full bg-teal" /> Principal {principalPct}%
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="h-2 w-2 rounded-full bg-amber-400" /> Interest {100 - principalPct}%
                  </span>
                </div>
              </div>
            </div>
          )}
          <Button className="mt-6 w-full" onClick={goApply} disabled={Boolean(inputError)}>
            Apply for this loan
          </Button>
        </Card>
      </div>

      <Card className="mt-6">
        <div className="mb-4 flex items-center gap-2">
          <Lightbulb className="h-5 w-5 text-teal" />
          <h2 className="text-lg font-semibold">What-if coach</h2>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="income" className="mb-1 block text-sm font-medium text-navy">
              Monthly income (₹)
            </label>
            <input
              id="income"
              type="number"
              min={1}
              value={Number.isNaN(income) ? '' : income}
              onChange={(e) => setIncome(e.target.value === '' ? NaN : Number(e.target.value))}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-teal focus:ring-2 focus:ring-teal/20"
            />
          </div>
          <div>
            <label htmlFor="existingEmi" className="mb-1 block text-sm font-medium text-navy">
              Existing EMIs (₹ / month)
            </label>
            <input
              id="existingEmi"
              type="number"
              min={0}
              value={Number.isNaN(existingEmi) ? '' : existingEmi}
              onChange={(e) => setExistingEmi(e.target.value === '' ? NaN : Number(e.target.value))}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-teal focus:ring-2 focus:ring-teal/20"
            />
          </div>
        </div>

        <div className="mt-5">
          {incomeError || inputError ? (
            <p className="text-sm text-slate-500">{incomeError || 'Fix the loan inputs above to see suggestions.'}</p>
          ) : !whatIf ? (
            <Spinner size="sm" />
          ) : (
            <div className={whatIfLoading ? 'opacity-60 transition-opacity' : 'transition-opacity'}>
              <div className="flex flex-wrap items-center gap-2 text-sm">
                <span className="text-slate-600">
                  Your FOIR: <span className="font-semibold text-navy">{whatIf.current.foir}%</span>
                </span>
                <InfoTip text="FOIR = share of your income going to EMIs; banks prefer under 50%" />
                <Badge variant={eligibilityVariant(whatIf.current.eligibility)}>
                  {ELIGIBILITY_LABELS[whatIf.current.eligibility]}
                </Badge>
              </div>
              {whatIf.options.length > 0 ? (
                <div className="mt-4">
                  <p className="mb-2 text-sm text-slate-500">Tap a suggestion to apply it:</p>
                  <div className="flex flex-wrap gap-2">
                    {whatIf.options.map((o) => (
                      <button
                        key={o.type}
                        onClick={() => applyOption(o)}
                        className="rounded-full border border-teal/40 bg-teal/5 px-4 py-2 text-left text-sm font-medium text-teal hover:bg-teal/10"
                      >
                        {o.label}
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                <p className="mt-3 text-sm text-slate-500">
                  {whatIf.current.eligibility === 'LIKELY_ELIGIBLE'
                    ? 'This plan already fits your budget well.'
                    : 'No simple change fits within 40% of your income. Try a smaller amount.'}
                </p>
              )}
            </div>
          )}
        </div>
      </Card>

      {result && !inputError && (
        <Card className="mt-6">
          <button
            onClick={() => setShowSchedule(!showSchedule)}
            className="flex w-full items-center justify-between text-left font-semibold text-navy"
          >
            {showSchedule ? 'Hide repayment schedule' : 'Show repayment schedule'}
            {showSchedule ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
          </button>
          {showSchedule && (
            <div className="mt-4 max-h-96 overflow-auto">
              <table className="w-full text-right text-sm">
                <thead className="sticky top-0 bg-white text-xs uppercase text-slate-500">
                  <tr>
                    <th className="py-2 text-left">Month</th>
                    <th className="py-2">EMI</th>
                    <th className="py-2">Interest</th>
                    <th className="py-2">Principal</th>
                    <th className="py-2">Balance</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {result.schedule.map((row) => (
                    <tr key={row.month}>
                      <td className="py-1.5 text-left text-slate-500">{row.month}</td>
                      <td className="py-1.5">{formatINR(row.emi)}</td>
                      <td className="py-1.5">{formatINR(row.interest)}</td>
                      <td className="py-1.5">{formatINR(row.principal)}</td>
                      <td className="py-1.5 font-medium text-navy">{formatINR(row.balance)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}
    </div>
  )
}
