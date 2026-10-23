import { Inbox } from 'lucide-react'

/** Shown when a list is empty; `action` is usually a Button that tells the user what to do next. */
export default function EmptyState({ title, message, action }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 px-6 py-12 text-center">
      <Inbox className="mb-3 h-10 w-10 text-slate-400" />
      <h3 className="text-base font-semibold">{title}</h3>
      {message && <p className="mt-1 max-w-sm text-sm text-slate-500">{message}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}
