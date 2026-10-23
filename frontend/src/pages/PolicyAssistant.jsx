import { useState } from 'react'
import toast from 'react-hot-toast'
import { FileText, Send } from 'lucide-react'
import client, { getErrorMessage } from '../api/client'
import Badge from '../components/Badge'
import Button from '../components/Button'
import Card from '../components/Card'
import EmptyState from '../components/EmptyState'
import PageHeader from '../components/PageHeader'

const SUGGESTIONS = [
  'Can I foreclose my vehicle loan after six months?',
  'What documents do I need if I am self-employed?',
  'What is the processing fee for a personal loan?',
  'What is the minimum credit score for a home loan?',
  'How long does disbursal take?',
]

const LOAN_TYPES = [
  { value: '', label: 'Any loan type' },
  { value: 'PERSONAL', label: 'Personal' },
  { value: 'HOME', label: 'Home' },
  { value: 'VEHICLE', label: 'Vehicle' },
  { value: 'EDUCATION', label: 'Education' },
]

const CONFIDENCE_VARIANT = { HIGH: 'success', MEDIUM: 'warning', LOW: 'neutral' }

function AnswerCard({ item }) {
  const { question, answer } = item
  return (
    <Card>
      <p className="text-sm font-medium text-slate-500">Q: {question}</p>
      <p className="mt-2 text-slate-800">{answer.answer}</p>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <Badge variant={CONFIDENCE_VARIANT[answer.confidence]}>{answer.confidence} confidence</Badge>
        {answer.sources.map((s) => (
          <span
            key={`${s.document}-${s.section}-${s.version}`}
            className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600"
          >
            <FileText className="h-3.5 w-3.5 text-teal" />
            {s.document} · {s.section} · v{s.version} · effective {s.effectiveDate}
          </span>
        ))}
      </div>
      {answer.followUpRequired && (
        <p className="mt-3 text-sm text-amber-700">Need more help? Contact a loan officer.</p>
      )}
    </Card>
  )
}

export default function PolicyAssistant() {
  const [question, setQuestion] = useState('')
  const [loanType, setLoanType] = useState('')
  const [loading, setLoading] = useState(false)
  const [history, setHistory] = useState([])

  async function ask(text) {
    const q = text.trim()
    if (q.length < 3) {
      toast.error('Please type a longer question.')
      return
    }
    setLoading(true)
    try {
      const body = { question: q }
      if (loanType) body.loanType = loanType
      const res = await client.post('/rag/ask', body)
      setHistory((h) => [{ id: Date.now(), question: q, answer: res.data }, ...h])
      setQuestion('')
    } catch (err) {
      toast.error(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader title="Policy Help" subtitle="Answers only from Kestrel Bank's approved documents" />

      <Card>
        <form
          onSubmit={(e) => {
            e.preventDefault()
            ask(question)
          }}
          className="flex flex-col gap-3 sm:flex-row"
        >
          <select
            value={loanType}
            onChange={(e) => setLoanType(e.target.value)}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-teal"
            aria-label="Loan type"
          >
            {LOAN_TYPES.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            maxLength={500}
            placeholder="Ask about fees, documents, foreclosure…"
            className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-teal focus:ring-2 focus:ring-teal/20"
          />
          <Button type="submit" loading={loading}>
            {!loading && <Send className="h-4 w-4" />} Ask
          </Button>
        </form>

        <div className="mt-4 flex flex-wrap gap-2">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              disabled={loading}
              onClick={() => ask(s)}
              className="rounded-full border border-teal/30 bg-teal/5 px-3 py-1.5 text-xs font-medium text-teal hover:bg-teal/10 disabled:opacity-50"
            >
              {s}
            </button>
          ))}
        </div>
      </Card>

      <div className="mt-6 space-y-4">
        {history.length === 0 && !loading ? (
          <EmptyState title="Ask your first question" message="Tap a suggestion above or type your own question." />
        ) : (
          history.map((item) => <AnswerCard key={item.id} item={item} />)
        )}
      </div>
    </div>
  )
}
