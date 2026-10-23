export default function Spinner({ size = 'md', label }) {
  const sizes = { sm: 'h-4 w-4 border-2', md: 'h-8 w-8 border-[3px]', lg: 'h-12 w-12 border-4' }
  return (
    <div className="flex flex-col items-center justify-center gap-2" role="status">
      <div className={`${sizes[size]} animate-spin rounded-full border-teal border-t-transparent`} />
      {label && <p className="text-sm text-slate-500">{label}</p>}
    </div>
  )
}
