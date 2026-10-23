import { useEffect, useState } from 'react'
import { ArrowDown, Bot, CheckCircle2, CircleDot, FileSearch, Flag, Gauge, MessageSquare, ShieldCheck, Workflow, XCircle, AlertTriangle } from 'lucide-react'
import client from '../api/client'
import Badge from './Badge'
import Card from './Card'

// Graph node -> the agent that ran it (names stored in agent_steps.agent_name).
const NODES = [
  { id: 'document', agent: 'DocumentVerificationAgent', label: 'Document Verification Agent', icon: FileSearch },
  { id: 'credit', agent: 'CreditAssessmentAgent', label: 'Credit Assessment Agent', icon: Gauge },
  { id: 'compliance', agent: 'ComplianceAgent', label: 'Compliance Agent', icon: ShieldCheck },
  { id: 'decide', agent: 'Orchestrator', label: 'Orchestrator (decide)', icon: Workflow },
]
const BRANCHES = [
  { id: 'request_docs', label: 'Request documents', hint: 'missing documents' },
  { id: 'under_review', label: 'Under review', hint: 'all documents present' },
]

function resultVariant(result) {
  if (['PASS', 'SENT', 'RECOMMEND_APPROVE'].includes(result)) return 'success'
  if (['FAIL', 'RECOMMEND_REJECT'].includes(result)) return 'danger'
  return 'warning'
}

function ResultIcon({ result }) {
  const v = resultVariant(result)
  if (v === 'success') return <CheckCircle2 className="h-4 w-4 text-emerald-600" />
  if (v === 'danger') return <XCircle className="h-4 w-4 text-red-600" />
  return <AlertTriangle className="h-4 w-4 text-amber-500" />
}

function Terminal({ label }) {
  return (
    <div className="mx-auto w-fit rounded-full border border-slate-300 bg-slate-50 px-4 py-1 text-xs font-semibold tracking-wide text-slate-500">
      {label}
    </div>
  )
}

function Arrow({ label }) {
  return (
    <div className="flex flex-col items-center py-1 text-slate-300">
      <ArrowDown className="h-4 w-4" />
      {label && <span className="text-[10px] text-slate-400">{label}</span>}
    </div>
  )
}

function AgentNode({ node, step }) {
  const Icon = node.icon
  const tools = step ? [...new Set(step.toolCalls.map((t) => t.tool))] : []
  return (
    <div
      className={`rounded-lg border px-3 py-2 ${step ? 'border-teal/50 bg-teal/5' : 'border-dashed border-slate-300 bg-white opacity-60'}`}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="flex items-center gap-2 text-sm font-medium text-navy">
          <Icon className="h-4 w-4 text-teal" /> {node.label}
          <code className="rounded bg-slate-100 px-1 text-[10px] text-slate-500">{node.id}</code>
        </span>
        {step && (
          <span className="flex items-center gap-1">
            <ResultIcon result={step.result} />
            <Badge variant={resultVariant(step.result)}>{step.result}</Badge>
          </span>
        )}
      </div>
      {step && (
        <>
          <p className="mt-1 text-xs text-slate-600">{step.detail}</p>
          {tools.length > 0 && (
            <p className="mt-1 text-[11px] text-slate-500">
              Tools: {tools.map((t) => <code key={t} className="mr-1 rounded bg-slate-100 px-1">{t}</code>)}
            </p>
          )}
        </>
      )}
    </div>
  )
}

/** Visual LangGraph run: the compiled graph's nodes, with the path this application actually took highlighted. */
export default function AgentWorkflow({ steps, latestRun }) {
  const [graph, setGraph] = useState(null)
  const [showDef, setShowDef] = useState(false)

  useEffect(() => {
    client
      .get('/analyst/workflow')
      .then((res) => setGraph(res.data))
      .catch(() => setGraph(null))
  }, [])

  if (!steps.length) {
    return (
      <Card>
        <h2 className="mb-1 flex items-center gap-2 font-semibold">
          <Bot className="h-5 w-5 text-teal" /> AI agent workflow
        </h2>
        <p className="text-sm text-slate-500">The LangGraph pipeline hasn't run for this application yet.</p>
      </Card>
    )
  }

  const byAgent = Object.fromEntries(steps.map((s) => [s.agentName, s]))
  const comms = byAgent.CustomerCommunicationAgent
  const takenBranch = latestRun?.missingDocuments?.length ? 'request_docs' : 'under_review'
  const toolCount = steps.reduce((n, s) => n + s.toolCalls.length, 0)

  return (
    <Card>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 font-semibold">
          <Bot className="h-5 w-5 text-teal" /> AI agent workflow (LangGraph)
        </h2>
        <span className="text-xs text-slate-500">
          {steps.length} agents ran · {toolCount} permission-checked tool calls
          {latestRun?.auditTrailId && <> · {latestRun.auditTrailId}</>}
        </span>
      </div>

      <Terminal label="START" />
      <Arrow />
      {NODES.map((node, i) => (
        <div key={node.id}>
          <AgentNode node={node} step={byAgent[node.agent]} />
          {i < NODES.length - 1 && <Arrow />}
        </div>
      ))}

      <Arrow label="conditional route" />
      <div className="grid grid-cols-2 gap-2">
        {BRANCHES.map((b) => {
          const taken = b.id === takenBranch
          return (
            <div
              key={b.id}
              className={`rounded-lg border px-3 py-2 ${taken ? 'border-teal bg-teal/10' : 'border-dashed border-slate-200 opacity-50'}`}
            >
              <p className="flex items-center gap-1 text-sm font-medium text-navy">
                {taken ? <Flag className="h-4 w-4 text-teal" /> : <CircleDot className="h-4 w-4 text-slate-300" />}
                {b.label}
                <code className="rounded bg-slate-100 px-1 text-[10px] text-slate-500">{b.id}</code>
              </p>
              <p className="text-[11px] text-slate-500">{taken ? 'Path taken' : 'Not taken'} · {b.hint}</p>
              {taken && comms && (
                <p className="mt-1 flex gap-1 text-xs text-slate-600">
                  <MessageSquare className="mt-0.5 h-3.5 w-3.5 shrink-0 text-teal" />
                  <span>
                    <span className="font-medium">Customer Communication Agent:</span> “{comms.detail}”
                  </span>
                </p>
              )}
            </div>
          )
        })}
      </div>
      <Arrow />
      <Terminal label="END → human analyst decides" />

      {graph && (
        <div className="mt-4 border-t border-slate-100 pt-3">
          <button onClick={() => setShowDef(!showDef)} className="text-xs font-medium text-teal hover:underline">
            {showDef ? 'Hide' : 'Show'} graph definition from LangGraph ({graph.nodes.length} nodes, {graph.edges.length} edges)
          </button>
          {showDef && (
            <pre className="mt-2 max-h-64 overflow-auto rounded bg-slate-900 p-3 text-[11px] text-slate-100">
              {graph.edges
                .map((e) => `${e.source} ${e.conditional ? '-.->' : '-->'} ${e.target}${e.conditional ? '   (conditional)' : ''}`)
                .join('\n')}
            </pre>
          )}
        </div>
      )}
    </Card>
  )
}
