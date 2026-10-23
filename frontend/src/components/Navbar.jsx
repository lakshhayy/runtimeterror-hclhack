import { useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { Landmark, LogOut, Menu, X } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { roleHome } from '../utils/labels'

const LINKS = {
  CUSTOMER: [
    { to: '/advisor', label: 'Advisor' },
    { to: '/products', label: 'Products' },
    { to: '/emi', label: 'EMI Calculator' },
    { to: '/policy', label: 'Policy Help' },
    { to: '/applications', label: 'My Applications' },
  ],
  OFFICER: [
    { to: '/officer/applications', label: 'Applications' },
    { to: '/policy', label: 'Policy Help' },
  ],
  ANALYST: [
    { to: '/analyst/queue', label: 'Review Queue' },
    { to: '/audit', label: 'Audit Log' },
    { to: '/policy', label: 'Policy Help' },
  ],
}

const ROLE_NAMES = { CUSTOMER: 'Customer', OFFICER: 'Loan Officer', ANALYST: 'Credit Analyst' }

export default function Navbar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const links = LINKS[user?.role] || []

  function handleLogout() {
    logout()
    navigate('/login', { replace: true })
  }

  const linkClass = ({ isActive }) =>
    `rounded-md px-3 py-2 text-sm font-medium transition-colors ${
      isActive ? 'bg-teal/10 text-teal' : 'text-slate-600 hover:bg-slate-100 hover:text-navy'
    }`

  return (
    <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/95 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4">
        <NavLink to={roleHome(user?.role)} className="flex items-center gap-2 font-bold text-navy">
          <Landmark className="h-6 w-6 text-teal" />
          LoanLens <span className="text-teal">AI</span>
        </NavLink>

        <nav className="hidden items-center gap-1 md:flex">
          {links.map((l) => (
            <NavLink key={l.to} to={l.to} className={linkClass}>
              {l.label}
            </NavLink>
          ))}
        </nav>

        <div className="hidden items-center gap-3 md:flex">
          <div className="text-right leading-tight">
            <p className="text-sm font-medium text-navy">{user?.fullName}</p>
            <p className="text-xs text-slate-500">{ROLE_NAMES[user?.role]}</p>
          </div>
          <button
            onClick={handleLogout}
            className="rounded-md p-2 text-slate-500 hover:bg-slate-100 hover:text-red-600"
            title="Log out"
          >
            <LogOut className="h-5 w-5" />
          </button>
        </div>

        <button className="rounded-md p-2 text-navy md:hidden" onClick={() => setOpen(!open)} aria-label="Menu">
          {open ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
        </button>
      </div>

      {open && (
        <div className="border-t border-slate-200 px-4 pb-4 md:hidden">
          <nav className="flex flex-col gap-1 pt-2">
            {links.map((l) => (
              <NavLink key={l.to} to={l.to} className={linkClass} onClick={() => setOpen(false)}>
                {l.label}
              </NavLink>
            ))}
          </nav>
          <div className="mt-3 flex items-center justify-between border-t border-slate-200 pt-3">
            <div>
              <p className="text-sm font-medium text-navy">{user?.fullName}</p>
              <p className="text-xs text-slate-500">{ROLE_NAMES[user?.role]}</p>
            </div>
            <button onClick={handleLogout} className="flex items-center gap-1 text-sm text-red-600">
              <LogOut className="h-4 w-4" /> Log out
            </button>
          </div>
        </div>
      )}
    </header>
  )
}
