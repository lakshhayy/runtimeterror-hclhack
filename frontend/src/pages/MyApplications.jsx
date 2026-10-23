import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { ChevronRight } from 'lucide-react'
import client, { getErrorMessage } from '../api/client'
import Badge from '../components/Badge'
import Button from '../components/Button'
import Card from '../components/Card'
import EmptyState from '../components/EmptyState'
import PageHeader from '../components/PageHeader'
import Spinner from '../components/Spinner'
import { formatDate, formatINR } from '../utils/format'
import { STATUS_LABELS, statusVariant } from '../utils/labels'

export default function MyApplications() {
  const navigate = useNavigate()
  const [apps, setApps] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    client
      .get('/applications/mine')
      .then((res) => setApps(res.data))
      .catch((err) => {
        setError(true)
        toast.error(getErrorMessage(err))
      })
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader
        title="My Applications"
        subtitle="Track the status of your loan applications"
        action={<Button onClick={() => navigate('/apply')}>New application</Button>}
      />
      {loading ? (
        <div className="py-16">
          <Spinner label="Loading your applications…" />
        </div>
      ) : error ? (
        <EmptyState
          title="Couldn't load your applications"
          message="Please refresh the page to try again."
          action={<Button onClick={() => window.location.reload()}>Refresh</Button>}
        />
      ) : apps.length === 0 ? (
        <EmptyState
          title="No applications yet"
          message="Tell our AI advisor what you need and apply in minutes."
          action={<Button onClick={() => navigate('/advisor')}>Talk to the advisor</Button>}
        />
      ) : (
        <div className="space-y-3">
          {apps.map((a) => (
            <Link key={a.id} to={`/applications/${a.id}`} className="block">
              <Card className="flex items-center justify-between gap-4 transition-shadow hover:shadow-md">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-semibold text-navy">{a.applicationId}</span>
                    <Badge variant={statusVariant(a.status)}>{STATUS_LABELS[a.status]}</Badge>
                  </div>
                  <p className="mt-1 truncate text-sm text-slate-600">
                    {a.productName} · {formatINR(a.amount)} · {a.tenureMonths} months
                  </p>
                  <p className="text-xs text-slate-400">Created {formatDate(a.createdAt)}</p>
                </div>
                <ChevronRight className="h-5 w-5 shrink-0 text-slate-400" />
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
