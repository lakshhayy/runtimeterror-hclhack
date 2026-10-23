import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { Flag } from 'lucide-react'
import client, { getErrorMessage } from '../api/client'
import Badge from '../components/Badge'
import Button from '../components/Button'
import Card from '../components/Card'
import EmptyState from '../components/EmptyState'
import PageHeader from '../components/PageHeader'
import Spinner from '../components/Spinner'
import { formatDate, formatINR } from '../utils/format'
import { recommendationLabel, riskVariant } from '../utils/labels'

export default function AnalystQueue() {
  const navigate = useNavigate()
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    client
      .get('/analyst/queue')
      .then((res) => setItems(res.data))
      .catch((err) => toast.error(getErrorMessage(err)))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div>
      <PageHeader title="Review Queue" subtitle="Applications waiting for a credit decision · priority first" />
      {loading ? (
        <div className="py-16">
          <Spinner label="Loading queue…" />
        </div>
      ) : items.length === 0 ? (
        <EmptyState title="Nothing waiting for review" message="New applications appear here after automated checks." />
      ) : (
        <Card className="overflow-x-auto p-0">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-3">Application</th>
                <th className="px-4 py-3">Customer</th>
                <th className="px-4 py-3">Product</th>
                <th className="px-4 py-3 text-right">Amount</th>
                <th className="px-4 py-3">Risk</th>
                <th className="px-4 py-3">Recommendation</th>
                <th className="px-4 py-3">Submitted</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {items.map((i) => (
                <tr key={i.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 font-medium text-navy">
                    <span className="flex items-center gap-1">
                      {i.priority && <Flag className="h-4 w-4 text-red-500" title="Priority" />}
                      {i.applicationId}
                    </span>
                  </td>
                  <td className="px-4 py-3">{i.customerName}</td>
                  <td className="px-4 py-3">{i.productName}</td>
                  <td className="px-4 py-3 text-right">{formatINR(i.amount)}</td>
                  <td className="px-4 py-3">
                    {i.riskBand ? <Badge variant={riskVariant(i.riskBand)}>{i.riskBand}</Badge> : '—'}
                  </td>
                  <td className="px-4 py-3">{recommendationLabel(i.recommendation)}</td>
                  <td className="px-4 py-3 text-slate-500">{formatDate(i.createdAt)}</td>
                  <td className="px-4 py-3 text-right">
                    <Button onClick={() => navigate(`/analyst/applications/${i.id}`)}>Review</Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  )
}
