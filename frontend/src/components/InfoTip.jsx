import { Info } from 'lucide-react'

/** An ⓘ icon that shows `text` on hover or keyboard focus. */
export default function InfoTip({ text }) {
  return (
    <span className="group relative inline-flex align-middle" tabIndex={0} aria-label={text}>
      <Info className="h-4 w-4 cursor-help text-slate-400" />
      <span className="pointer-events-none absolute bottom-full left-1/2 z-20 mb-2 w-56 -translate-x-1/2 rounded-md bg-navy px-3 py-2 text-xs font-normal text-white opacity-0 shadow-lg transition-opacity group-hover:opacity-100 group-focus:opacity-100">
        {text}
      </span>
    </span>
  )
}
