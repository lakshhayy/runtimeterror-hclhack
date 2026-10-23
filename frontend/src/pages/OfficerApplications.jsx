import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import client, { getErrorMessage } from '../api/client'
import Badge from '../components/Badge'
import Card from '../components/Card'
import EmptyState from '../components/EmptyState'
import PageHeader from '../components/PageHeader'
import Spinner from '../components/Spinner'
import { formatDate, formatINR } from '../utils/format'
import { STATUS_LABELS, recommendationLabel, riskVariant, statusVariant } from '../utils/labels'

export default function OfficerApplications() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    client
      .get('/officer/applications')
      .then((res) => setItems(res.data))
      .catch((err) => toast.error(getErrorMessage(err)))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div>
      <PageHeader title="All Applications" subtitle="Read-only view of every application" />
      {loading ? (
        <div className="py-16">
          <Spinner label="Loading applications…" />
        </div>
      ) : items.length === 0 ? (
        <EmptyState title="No applications yet" message="Applications appear here once customers create them." />
      ) : (
        <Card className="overflow-x-auto p-0">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-3">Application</th>
                <th className="px-4 py-3">Customer</th>
                <th className="px-4 py-3">Product</th>
                <th className="px-4 py-3 text-right">Amount</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Risk</th>
                <th className="px-4 py-3">Recommendation</th>
                <th className="px-4 py-3">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {items.map((i) => (
                <tr key={i.id}>
                  <td className="px-4 py-3 font-medium text-navy">{i.applicationId}</td>
                  <td className="px-4 py-3">{i.customerName}</td>
                  <td className="px-4 py-3">{i.productName}</td>
                  <td className="px-4 py-3 text-right">{formatINR(i.amount)}</td>
                  <td className="px-4 py-3">
                    <Badge variant={statusVariant(i.status)}>{STATUS_LABELS[i.status]}</Badge>
                  </td>
                  <td className="px-4 py-3">
                    {i.riskBand ? <Badge variant={riskVariant(i.riskBand)}>{i.riskBand}</Badge> : '—'}
                  </td>
                  <td className="px-4 py-3">{recommendationLabel(i.recommendation)}</td>
                  <td className="px-4 py-3 text-slate-500">{formatDate(i.createdAt)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  )
}
