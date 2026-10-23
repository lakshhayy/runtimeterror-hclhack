import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Bot, Send, Sparkles } from 'lucide-react'
import client, { getErrorMessage } from '../api/client'
import Badge from '../components/Badge'
import Button from '../components/Button'
import Card from '../components/Card'
import { formatINR } from '../utils/format'
import { ELIGIBILITY_LABELS, eligibilityVariant } from '../utils/labels'

const SUGGESTIONS = [
  'I need ₹5 lakh for a used car, I earn ₹60,000, EMI below ₹12,000',
  'Mujhe 30 lakh ka home loan chahiye, salary 1.2 lakh',
  'Education loan of ₹8 lakh for my masters',
]

function RecommendationCard({ rec }) {
  const navigate = useNavigate()
  const years = (rec.tenureMonths / 12).toFixed(rec.tenureMonths % 12 ? 1 : 0)
  return (
    <Card className="flex flex-col">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="font-semibold">{rec.productName}</h3>
          <p className="text-xs text-slate-400">{rec.productId}</p>
        </div>
        <Badge variant={eligibilityVariant(rec.eligibilityIndicator)}>
          {ELIGIBILITY_LABELS[rec.eligibilityIndicator]}
        </Badge>
      </div>
      <p className="mt-3 text-3xl font-bold text-navy">
        {formatINR(rec.estimatedEmi)}
        <span className="text-base font-medium text-slate-400">/month</span>
      </p>
      <p className="mt-1 text-sm text-slate-500">
        {rec.tenureMonths} months ({years} yrs) · {rec.indicativeInterestRate.toFixed(2)}% p.a.
      </p>
      <p className="mt-3 text-sm text-slate-700">{rec.reason}</p>
      <div className="mt-4 flex flex-col gap-2 sm:flex-row">
        <Button
          className="flex-1"
          onClick={() => navigate(`/apply?productId=${rec.productId}&amount=${rec.amount}&tenure=${rec.tenureMonths}`)}
        >
          Apply with this
        </Button>
        <Button
          variant="secondary"
          className="flex-1"
          onClick={() =>
            navigate(
              `/emi?amount=${rec.amount}&rate=${rec.indicativeInterestRate}&tenure=${rec.tenureMonths}&productId=${rec.productId}`,
            )
          }
        >
          See EMI breakdown
        </Button>
      </div>
    </Card>
  )
}

function AssistantReply({ data }) {
  return (
    <div className="space-y-3">
      <p className="text-xs font-medium uppercase tracking-wide text-teal">{data.interpretedRequirement}</p>
      {data.recommendations.length > 0 ? (
        <>
          <div className="grid gap-4 md:grid-cols-2">
            {data.recommendations.map((rec) => (
              <RecommendationCard key={rec.productId} rec={{ ...rec, amount: data.loanAmount }} />
            ))}
          </div>
          <p className="text-xs text-slate-400">{data.disclaimer}</p>
        </>
      ) : (
        <div className="inline-block rounded-2xl rounded-tl-sm bg-slate-100 px-4 py-3 text-slate-800">
          {data.clarifyingQuestion}
        </div>
      )}
    </div>
  )
}

export default function Advisor() {
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, loading])

  async function send(text) {
    const message = text.trim()
    if (message.length < 3 || loading) return
    setMessages((m) => [...m, { id: Date.now(), role: 'user', text: message }])
    setInput('')
    setLoading(true)
    try {
      const res = await client.post('/advisor/chat', { message })
      setMessages((m) => [...m, { id: Date.now() + 1, role: 'assistant', data: res.data }])
    } catch (err) {
      setMessages((m) => [...m, { id: Date.now() + 1, role: 'error', text: getErrorMessage(err) }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-4xl">
      <div className="mb-6 rounded-2xl bg-gradient-to-br from-navy to-[#134074] px-6 py-8 text-white">
        <div className="mb-2 flex items-center gap-2 text-sm text-teal">
          <Sparkles className="h-4 w-4" /> AI Loan Advisor
        </div>
        <h1 className="text-2xl font-bold text-white sm:text-3xl">What do you need a loan for?</h1>
        <p className="mt-1 text-sm text-slate-300">Describe it in your own words, in English or Hinglish.</p>
        <form
          onSubmit={(e) => {
            e.preventDefault()
            send(input)
          }}
          className="mt-5 flex gap-2"
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            maxLength={500}
            placeholder="e.g. I need 5 lakh for a used car…"
            className="flex-1 rounded-xl border-0 px-4 py-3 text-slate-800 outline-none ring-2 ring-transparent focus:ring-teal"
          />
          <Button type="submit" loading={loading} className="rounded-xl px-5">
            {!loading && <Send className="h-4 w-4" />} Send
          </Button>
        </form>
        <div className="mt-4 flex flex-wrap gap-2">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              disabled={loading}
              onClick={() => send(s)}
              className="rounded-full bg-white/10 px-3 py-1.5 text-left text-xs text-white hover:bg-white/20 disabled:opacity-50"
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-5">
        {messages.map((m) =>
          m.role === 'user' ? (
            <div key={m.id} className="flex justify-end">
              <div className="max-w-[85%] rounded-2xl rounded-tr-sm bg-teal px-4 py-3 text-white">{m.text}</div>
            </div>
          ) : (
            <div key={m.id} className="flex gap-3">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-navy">
                <Bot className="h-4 w-4 text-teal" />
              </div>
              <div className="min-w-0 flex-1">
                {m.role === 'assistant' ? (
                  <AssistantReply data={m.data} />
                ) : (
                  <div className="inline-block rounded-2xl rounded-tl-sm bg-red-50 px-4 py-3 text-red-700">{m.text}</div>
                )}
              </div>
            </div>
          ),
        )}
        {loading && (
          <div className="flex items-center gap-3 text-sm text-slate-500">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-navy">
              <Bot className="h-4 w-4 text-teal" />
            </div>
            Thinking…
          </div>
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
