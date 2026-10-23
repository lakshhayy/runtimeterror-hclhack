import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import { AlertTriangle, ArrowLeft, CheckCircle2, ShieldCheck, XCircle } from 'lucide-react'
import client, { getErrorMessage } from '../api/client'
import AgentWorkflow from '../components/AgentWorkflow'
import Badge from '../components/Badge'
import Button from '../components/Button'
import Card from '../components/Card'
import Spinner from '../components/Spinner'
import { formatINR } from '../utils/format'
import { DOC_LABELS, STATUS_LABELS, recommendationLabel, riskVariant, statusVariant } from '../utils/labels'

const TEMPLATES = ['Address proof missing', 'Income could not be verified', 'All checks satisfactory']
const CHECK_AGENTS = ['DocumentVerificationAgent', 'CreditAssessmentAgent', 'ComplianceAgent']

function CheckIcon({ result }) {
  if (result === 'PASS') return <CheckCircle2 className="h-5 w-5 text-emerald-600" />
  if (result === 'FAIL') return <XCircle className="h-5 w-5 text-red-600" />
  return <AlertTriangle className="h-5 w-5 text-amber-500" />
}

export default function AnalystReview() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [detail, setDetail] = useState(null)
  const [visible, setVisible] = useState(0)
  const [comment, setComment] = useState('')
  const [busy, setBusy] = useState(null)

  const load = useCallback(
    () =>
      client
        .get(`/analyst/applications/${id}`)
        .then((res) => setDetail(res.data))
        .catch((err) => toast.error(getErrorMessage(err))),
    [id],
  )

  useEffect(() => {
    load()
  }, [load])

  // Reveal agent checks one by one.
  const checkSteps = detail ? detail.steps.filter((s) => CHECK_AGENTS.includes(s.agentName)) : []
  useEffect(() => {
    if (visible >= checkSteps.length) return
    const t = setTimeout(() => setVisible((v) => v + 1), 400)
    return () => clearTimeout(t)
  }, [visible, checkSteps.length])

  async function decide(decision) {
    if (comment.trim().length < 5) {
      toast.error('Please add a comment (at least 5 characters).')
      return
    }
    setBusy(decision)
    try {
      await client.post(`/analyst/decision/${id}`, { decision, comment: comment.trim(), version: detail.application.version })
      toast.success('Decision recorded')
      navigate('/analyst/queue')
    } catch (err) {
      toast.error(getErrorMessage(err))
      if (err.response?.status === 409) load()
      setBusy(null)
    }
  }

  if (!detail) {
    return (
      <div className="py-20">
        <Spinner label="Loading application…" />
      </div>
    )
  }

  const { application: app, product, customer, documents, latestRun } = detail
  const canDecide = app.status === 'UNDER_REVIEW'

  return (
    <div className="pb-40 md:pb-0">
      <Link to="/analyst/queue" className="mb-4 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-navy">
        <ArrowLeft className="h-4 w-4" /> Review queue
      </Link>
      <div className="mb-6 flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-bold">{app.applicationId}</h1>
        <Badge variant={statusVariant(app.status)}>{STATUS_LABELS[app.status]}</Badge>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="space-y-6">
          <Card>
            <h2 className="mb-3 font-semibold">Applicant</h2>
            <dl className="grid grid-cols-2 gap-2 text-sm">
              <dt className="text-slate-500">Name</dt>
              <dd className="font-medium text-navy">{customer.fullName}</dd>
              <dt className="text-slate-500">Segment</dt>
              <dd className="font-medium text-navy">{customer.segment || '—'}</dd>
              <dt className="text-slate-500">Monthly income</dt>
              <dd className="font-medium text-navy">{formatINR(customer.monthlyIncome)}</dd>
              <dt className="text-slate-500">Existing EMIs</dt>
              <dd className="font-medium text-navy">{formatINR(customer.existingEmi)}</dd>
              <dt className="text-slate-500">PAN</dt>
              <dd className="font-medium text-navy">{customer.panMasked || '—'}</dd>
            </dl>
          </Card>
          <Card>
            <h2 className="mb-3 font-semibold">Loan</h2>
            <dl className="grid grid-cols-2 gap-2 text-sm">
              <dt className="text-slate-500">Product</dt>
              <dd className="font-medium text-navy">{product.name}</dd>
              <dt className="text-slate-500">Amount</dt>
              <dd className="font-medium text-navy">{formatINR(app.amount)}</dd>
              <dt className="text-slate-500">Tenure</dt>
              <dd className="font-medium text-navy">{app.tenureMonths} months</dd>
              <dt className="text-slate-500">Indicative EMI</dt>
              <dd className="font-medium text-navy">{formatINR(detail.indicativeEmi)}</dd>
              <dt className="text-slate-500">Documents</dt>
              <dd className="font-medium text-navy">
                {documents.length ? documents.map((d) => DOC_LABELS[d.docType]).join(', ') : 'None'}
              </dd>
            </dl>
          </Card>
        </div>

        <div className="space-y-4">
          <h2 className="font-semibold">AI agent checks</h2>
          {checkSteps.slice(0, visible).map((s) => (
            <Card key={s.stepOrder} className="animate-[fadeIn_0.3s_ease-out]">
              <div className="flex gap-3">
                <CheckIcon result={s.result} />
                <div className="min-w-0 flex-1">
                  <p className="font-medium text-navy">
                    {s.agentName} · {s.result}
                  </p>
                  <p className="text-sm text-slate-600">{s.detail}</p>
                  <details className="mt-2">
                    <summary className="cursor-pointer text-xs text-teal">Tool calls ({s.toolCalls.length})</summary>
                    <pre className="mt-2 max-h-48 overflow-auto rounded bg-slate-900 p-3 text-xs text-slate-100">
                      {JSON.stringify(s.toolCalls, null, 2)}
                    </pre>
                  </details>
                </div>
              </div>
            </Card>
          ))}
          {latestRun && visible >= checkSteps.length && (
            <Card className="border-teal/40 bg-teal/5">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-semibold text-navy">{recommendationLabel(latestRun.recommendation)}</span>
                <Badge variant={riskVariant(latestRun.riskBand)}>{latestRun.riskBand} risk</Badge>
              </div>
              <p className="mt-2 flex items-center gap-1 text-sm text-slate-600">
                <ShieldCheck className="h-4 w-4 text-teal" /> Requires human approval — AI agents cannot approve loans.
              </p>
              <p className="mt-2 text-sm text-slate-500">Customer message: “{latestRun.customerMessage}”</p>
            </Card>
          )}
        </div>
      </div>

      <div className="mt-6">
        <AgentWorkflow steps={detail.steps} latestRun={latestRun} />
      </div>

      {canDecide && (
        <Card className="fixed inset-x-0 bottom-0 z-20 rounded-none border-x-0 md:static md:mt-6 md:rounded-xl md:border-x">
          <h2 className="mb-2 font-semibold">Your decision</h2>
          <div className="mb-2 flex flex-wrap gap-2">
            {TEMPLATES.map((t) => (
              <button
                key={t}
                onClick={() => setComment(t)}
                className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600 hover:bg-slate-200"
              >
                {t}
              </button>
            ))}
          </div>
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            rows={2}
            maxLength={500}
            placeholder="Comment (required)"
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-teal focus:ring-2 focus:ring-teal/20"
          />
          <div className="mt-3 flex flex-col gap-2 sm:flex-row">
            <Button variant="success" className="flex-1" loading={busy === 'APPROVE'} disabled={busy !== null} onClick={() => decide('APPROVE')}>
              Approve
            </Button>
            <Button
              variant="warning"
              className="flex-1"
              loading={busy === 'REQUEST_DOCUMENTS'}
              disabled={busy !== null}
              onClick={() => decide('REQUEST_DOCUMENTS')}
            >
              Request documents
            </Button>
            <Button variant="danger" className="flex-1" loading={busy === 'REJECT'} disabled={busy !== null} onClick={() => decide('REJECT')}>
              Reject
            </Button>
          </div>
        </Card>
      )}
    </div>
  )
}
