import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import { ArrowLeft, Check, CheckCircle2, Info, MessageSquare, XCircle, AlertTriangle } from 'lucide-react'
import client, { getErrorMessage } from '../api/client'
import Badge from '../components/Badge'
import Button from '../components/Button'
import Card from '../components/Card'
import DocumentUploadRow from '../components/DocumentUploadRow'
import EmptyState from '../components/EmptyState'
import Spinner from '../components/Spinner'
import { formatDate, formatINR } from '../utils/format'
import { DOC_LABELS, STATUS_LABELS, statusVariant } from '../utils/labels'

const PATH = ['DRAFT', 'SUBMITTED', 'UNDER_VERIFICATION', 'UNDER_REVIEW', 'DECISION']
const FINAL = ['APPROVED', 'REJECTED', 'DISBURSED']

function Timeline({ status, timeline }) {
  const currentIndex = FINAL.includes(status) ? 4 : PATH.indexOf(status)
  const lastTime = (to) => [...timeline].reverse().find((t) => (Array.isArray(to) ? to.includes(t.toStatus) : t.toStatus === to))

  return (
    <ol className="space-y-0">
      {PATH.map((step, i) => {
        const done = i <= currentIndex
        const isDecision = step === 'DECISION'
        const entry = isDecision ? lastTime(FINAL) : lastTime(step)
        const rejected = isDecision && status === 'REJECTED'
        const label = isDecision ? (FINAL.includes(status) ? STATUS_LABELS[status] : 'Decision') : STATUS_LABELS[step]
        return (
          <li key={step} className="relative flex gap-3 pb-5 last:pb-0">
            {i < PATH.length - 1 && (
              <span className={`absolute left-3.5 top-7 h-full w-px ${i < currentIndex ? 'bg-teal' : 'bg-slate-200'}`} />
            )}
            <span
              className={`relative z-10 flex h-7 w-7 shrink-0 items-center justify-center rounded-full ${
                rejected ? 'bg-red-600 text-white' : done ? 'bg-teal text-white' : 'border-2 border-slate-200 bg-white'
              }`}
            >
              {rejected ? <XCircle className="h-4 w-4" /> : done ? <Check className="h-4 w-4" /> : null}
            </span>
            <div>
              <p className={`text-sm font-medium ${done ? 'text-navy' : 'text-slate-400'}`}>{label}</p>
              {done && entry && <p className="text-xs text-slate-500">{formatDate(entry.createdAt)}</p>}
            </div>
          </li>
        )
      })}
    </ol>
  )
}

const CHECK_ICONS = {
  PASS: <CheckCircle2 className="h-5 w-5 text-emerald-600" />,
  FAIL: <XCircle className="h-5 w-5 text-red-600" />,
}

const AGENT_NAMES = {
  DocumentVerificationAgent: 'Document check',
  CreditAssessmentAgent: 'Credit check',
  ComplianceAgent: 'Compliance check',
}

export default function ApplicationDetail() {
  const { id } = useParams()
  const [detail, setDetail] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [acting, setActing] = useState(false)

  const load = useCallback(
    () =>
      client
        .get(`/applications/${id}`)
        .then((res) => {
          setDetail(res.data)
          setError(false)
        })
        .catch((err) => {
          setError(true)
          toast.error(getErrorMessage(err))
        })
        .finally(() => setLoading(false)),
    [id],
  )

  useEffect(() => {
    load()
  }, [load])

  async function act(path, successMessage) {
    setActing(true)
    try {
      await client.post(`/applications/${id}/${path}`)
      toast.success(successMessage)
    } catch (err) {
      toast.error(getErrorMessage(err))
    } finally {
      await load()
      setActing(false)
    }
  }

  if (loading) {
    return (
      <div className="py-20">
        <Spinner label="Loading application…" />
      </div>
    )
  }
  if (error || !detail) {
    return (
      <EmptyState
        title="Couldn't load this application"
        message="It may not exist, or you may not have access to it."
        action={
          <Link to="/applications">
            <Button variant="secondary">Back to my applications</Button>
          </Link>
        }
      />
    )
  }

  const { application: app, product, documents, latestRun, latestRunStatus, timeline, latestDecision } = detail
  const docsByType = Object.fromEntries(documents.map((d) => [d.docType, d]))
  const canUpload = app.status === 'DRAFT' || app.status === 'UNDER_VERIFICATION'
  const uploadTypes =
    app.status === 'UNDER_VERIFICATION' && detail.missingDocTypes.length === 0
      ? ['IDENTITY', 'ADDRESS', 'INCOME'] // analyst asked for docs: allow replacing any
      : detail.missingDocTypes

  return (
    <div className="mx-auto max-w-4xl">
      <Link to="/applications" className="mb-4 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-navy">
        <ArrowLeft className="h-4 w-4" /> My applications
      </Link>

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-bold">{app.applicationId}</h1>
        <Badge variant={statusVariant(app.status)}>{STATUS_LABELS[app.status]}</Badge>
      </div>
      <p className="mb-5 text-sm text-slate-600">
        {product.name} · {formatINR(app.amount)} · {app.tenureMonths} months
      </p>

      <div className="mb-6 flex items-start gap-3 rounded-xl bg-teal px-5 py-4 text-white">
        <Info className="mt-0.5 h-5 w-5 shrink-0" />
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-white/80">Next step</p>
          <p className="font-medium">{detail.nextStep}</p>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-5">
        <Card className="md:col-span-2">
          <h2 className="mb-4 font-semibold">Progress</h2>
          <Timeline status={app.status} timeline={timeline} />
        </Card>

        <div className="space-y-6 md:col-span-3">
          {latestRun && (
            <Card>
              <div className="mb-3 flex items-center gap-2">
                <MessageSquare className="h-5 w-5 text-teal" />
                <h2 className="font-semibold">Message from Kestrel Bank</h2>
              </div>
              <p className="text-slate-700">{latestRun.customerMessage}</p>
            </Card>
          )}

          {latestRunStatus === 'FAILED' && (
            <Card className="border-amber-200 bg-amber-50">
              <p className="text-sm text-amber-800">Our automated checks didn't finish. Please click "Re-run checks" below.</p>
            </Card>
          )}

          {latestRun && (
            <Card>
              <h2 className="mb-3 font-semibold">Automated checks</h2>
              <ul className="space-y-3">
                {latestRun.checks.map((c) => (
                  <li key={c.agent} className="flex gap-3">
                    {CHECK_ICONS[c.result] || <AlertTriangle className="h-5 w-5 text-amber-500" />}
                    <div>
                      <p className="text-sm font-medium text-navy">
                        {AGENT_NAMES[c.agent] || c.agent} · {c.result}
                      </p>
                      <p className="text-sm text-slate-600">{c.detail}</p>
                    </div>
                  </li>
                ))}
              </ul>
            </Card>
          )}

          {latestDecision && (
            <Card>
              <h2 className="mb-2 font-semibold">Analyst's note</h2>
              <p className="text-slate-700">{latestDecision.comment}</p>
              <p className="mt-1 text-xs text-slate-400">{formatDate(latestDecision.createdAt)}</p>
            </Card>
          )}

          {canUpload && (
            <Card>
              <h2 className="mb-1 font-semibold">{app.status === 'DRAFT' ? 'Finish your application' : 'Upload documents'}</h2>
              <p className="mb-4 text-sm text-slate-500">
                Uploaded:{' '}
                {documents.length ? documents.map((d) => DOC_LABELS[d.docType]).join(', ') : 'none yet'}
              </p>
              <div className="space-y-3">
                {uploadTypes.map((t) => (
                  <DocumentUploadRow
                    key={t}
                    appId={app.id}
                    docType={t}
                    label={DOC_LABELS[t]}
                    uploaded={docsByType[t]}
                    onUploaded={load}
                  />
                ))}
              </div>
              {app.status === 'DRAFT' ? (
                <Button className="mt-4 w-full" loading={acting} onClick={() => act('submit', 'Application submitted')}>
                  {acting ? 'AI agents are checking your application…' : 'Submit application'}
                </Button>
              ) : (
                <>
                  <Button
                    className="mt-4 w-full"
                    loading={acting}
                    disabled={detail.missingDocTypes.length > 0}
                    onClick={() => act('recheck', 'Documents submitted for checks')}
                  >
                    {acting
                      ? 'AI agents are re-checking…'
                      : latestRunStatus === 'FAILED'
                        ? 'Re-run checks'
                        : 'Submit documents'}
                  </Button>
                  {detail.missingDocTypes.length > 0 && (
                    <p className="mt-2 text-center text-xs text-slate-500">Upload the missing documents first.</p>
                  )}
                </>
              )}
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
