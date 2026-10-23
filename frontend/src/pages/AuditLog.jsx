import { Fragment, useCallback, useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { ChevronDown, ChevronRight, RefreshCw, ShieldCheck, ShieldAlert } from 'lucide-react'
import client, { getErrorMessage } from '../api/client'
import Badge from '../components/Badge'
import Button from '../components/Button'
import Card from '../components/Card'
import EmptyState from '../components/EmptyState'
import PageHeader from '../components/PageHeader'
import Spinner from '../components/Spinner'
import { formatDate } from '../utils/format'

const STATUS_VARIANT = { SUCCESS: 'success', DENIED: 'danger', BLOCKED: 'danger', ERROR: 'warning' }

function AuditRow({ entry }) {
  const [open, setOpen] = useState(false)
  const hasDetail = entry.inputMasked != null || entry.output != null
  return (
    <Fragment>
      <tr
        onClick={() => hasDetail && setOpen(!open)}
        className={`${hasDetail ? 'cursor-pointer' : ''} hover:bg-slate-50 ${entry.status !== 'SUCCESS' ? 'bg-red-50/40' : ''}`}
      >
        <td className="whitespace-nowrap px-3 py-2 text-slate-500">
          <span className="flex items-center gap-1">
            {hasDetail ? open ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" /> : <span className="w-3.5" />}
            {formatDate(entry.createdAt)}
          </span>
        </td>
        <td className="px-3 py-2 font-mono text-xs">{entry.actor}</td>
        <td className="px-3 py-2 font-medium text-navy">{entry.action}</td>
        <td className="px-3 py-2 font-mono text-xs text-slate-600">{entry.entity || '—'}</td>
        <td className="px-3 py-2">
          <Badge variant={STATUS_VARIANT[entry.status] || 'neutral'}>{entry.status}</Badge>
        </td>
      </tr>
      {open && (
        <tr>
          <td colSpan={5} className="bg-slate-50 px-3 py-3">
            <div className="grid gap-3 md:grid-cols-2">
              <div>
                <p className="mb-1 text-xs font-semibold text-slate-500">Input (PII masked)</p>
                <pre className="max-h-56 overflow-auto rounded bg-slate-900 p-2 text-[11px] text-slate-100">
                  {JSON.stringify(entry.inputMasked, null, 2) ?? 'null'}
                </pre>
              </div>
              <div>
                <p className="mb-1 text-xs font-semibold text-slate-500">Output</p>
                <pre className="max-h-56 overflow-auto rounded bg-slate-900 p-2 text-[11px] text-slate-100">
                  {JSON.stringify(entry.output, null, 2) ?? 'null'}
                </pre>
              </div>
            </div>
            {entry.requestId && <p className="mt-2 text-[11px] text-slate-400">Request ID: {entry.requestId}</p>}
          </td>
        </tr>
      )}
    </Fragment>
  )
}

function GuardrailTest({ onDone }) {
  const [appId, setAppId] = useState('')
  const [apps, setApps] = useState([])
  const [busy, setBusy] = useState(false)
  const [results, setResults] = useState(null)

  useEffect(() => {
    client
      .get('/officer/applications')
      .then((res) => {
        setApps(res.data)
        if (res.data.length) setAppId(String(res.data[0].id))
      })
      .catch(() => setApps([]))
  }, [])

  async function run() {
    setBusy(true)
    try {
      const res = await client.post(`/audit/guardrail-test/${appId}`)
      setResults(res.data.results)
      const blocked = res.data.results.filter((r) => r.blocked).length
      toast.success(`${blocked}/${res.data.results.length} attacks blocked`)
      onDone()
    } catch (err) {
      toast.error(getErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card className="mb-6">
      <div className="mb-3 flex items-center gap-2">
        <ShieldCheck className="h-5 w-5 text-teal" />
        <h2 className="font-semibold">Run guardrail test</h2>
      </div>
      <p className="mb-3 text-sm text-slate-600">
        Fires 3 real attacks at an application: an agent using a tool it isn't allowed, an agent trying to approve, and a
        prompt injection. Each attempt is blocked and recorded below.
      </p>
      {apps.length === 0 ? (
        <p className="text-sm text-slate-500">Create an application first to run the test against it.</p>
      ) : (
        <div className="flex flex-col gap-2 sm:flex-row">
          <select
            value={appId}
            onChange={(e) => setAppId(e.target.value)}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-teal"
            aria-label="Application"
          >
            {apps.map((a) => (
              <option key={a.id} value={a.id}>
                {a.applicationId} · {a.customerName} · {a.status}
              </option>
            ))}
          </select>
          <Button onClick={run} loading={busy} disabled={!appId}>
            Run guardrail test
          </Button>
        </div>
      )}
      {results && (
        <ul className="mt-4 space-y-2">
          {results.map((r) => (
            <li key={r.test} className="flex items-start gap-3 rounded-lg border border-slate-200 p-3">
              {r.blocked ? (
                <Badge variant="success">🛡️ Blocked</Badge>
              ) : (
                <Badge variant="danger">
                  <ShieldAlert className="mr-1 h-3 w-3" /> Not blocked
                </Badge>
              )}
              <div className="min-w-0">
                <p className="text-sm font-medium text-navy">{r.test}</p>
                <p className="break-words text-xs text-slate-500">{r.message}</p>
              </div>
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}

export default function AuditLog() {
  const [tab, setTab] = useState('all')
  const [appFilter, setAppFilter] = useState('')
  const [entries, setEntries] = useState([])
  const [loading, setLoading] = useState(true)
  const [reload, setReload] = useState(0)

  const load = useCallback(() => {
    const appId = appFilter.trim().replace(/^LA-2026-0*/i, '')
    const url = tab === 'security' ? '/audit/security' : '/audit'
    const params = tab === 'all' && appId ? { applicationId: appId, limit: 200 } : { limit: 200 }
    return client
      .get(url, { params })
      .then((res) => setEntries(res.data))
      .catch((err) => toast.error(getErrorMessage(err)))
      .finally(() => setLoading(false))
  }, [tab, appFilter])

  useEffect(() => {
    const t = setTimeout(load, 300)
    return () => clearTimeout(t)
  }, [load, reload])

  return (
    <div>
      <PageHeader
        title="Audit Log"
        subtitle="Every login, AI request, agent tool call, status change and decision (PII masked)"
        action={
          <Button variant="secondary" onClick={() => setReload((n) => n + 1)}>
            <RefreshCw className="h-4 w-4" /> Refresh
          </Button>
        }
      />

      <GuardrailTest
        onDone={() => {
          setTab('security')
          setReload((n) => n + 1)
        }}
      />

      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex gap-2">
          {[
            ['all', 'All activity'],
            ['security', 'Security events'],
          ].map(([key, label]) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={`rounded-full px-4 py-1.5 text-sm font-medium ${
                tab === key ? 'bg-navy text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        {tab === 'all' && (
          <input
            value={appFilter}
            onChange={(e) => setAppFilter(e.target.value)}
            placeholder="Filter by application (e.g. 7 or LA-2026-00007)"
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-teal focus:ring-2 focus:ring-teal/20 sm:w-80"
          />
        )}
      </div>

      {loading ? (
        <div className="py-16">
          <Spinner label="Loading audit log…" />
        </div>
      ) : entries.length === 0 ? (
        <EmptyState title="No audit entries" message="Activity will appear here as people use the app." />
      ) : (
        <Card className="overflow-x-auto p-0">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-3 py-3">Time (IST)</th>
                <th className="px-3 py-3">Actor</th>
                <th className="px-3 py-3">Action</th>
                <th className="px-3 py-3">Entity</th>
                <th className="px-3 py-3">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {entries.map((e) => (
                <AuditRow key={e.id} entry={e} />
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  )
}
