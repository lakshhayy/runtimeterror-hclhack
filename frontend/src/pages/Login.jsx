import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { Briefcase, Landmark, ShieldCheck, User } from 'lucide-react'
import { getErrorMessage } from '../api/client'
import Button from '../components/Button'
import Card from '../components/Card'
import { useAuth } from '../context/AuthContext'
import { roleHome } from '../utils/labels'

const QUICK_LOGINS = [
  { label: 'Continue as Customer (Priya)', email: 'priya@loanlens.com', password: 'Customer@123', icon: User },
  { label: 'Loan Officer', email: 'officer@loanlens.com', password: 'Officer@123', icon: Briefcase },
  { label: 'Credit Analyst', email: 'analyst@loanlens.com', password: 'Analyst@123', icon: ShieldCheck },
]

export default function Login() {
  const { user, login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(null) // "form" or the quick-login email being used

  if (user) return <Navigate to={roleHome(user.role)} replace />

  async function doLogin(loginEmail, loginPassword, source) {
    setBusy(source)
    try {
      const u = await login(loginEmail, loginPassword)
      toast.success(`Welcome, ${u.fullName}`)
      navigate(roleHome(u.role), { replace: true })
    } catch (err) {
      toast.error(getErrorMessage(err))
    } finally {
      setBusy(null)
    }
  }

  function handleSubmit(e) {
    e.preventDefault()
    doLogin(email.trim(), password, 'form')
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-50 to-teal/10 px-4 py-10">
      <div className="w-full max-w-md">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-navy">
            <Landmark className="h-7 w-7 text-teal" />
          </div>
          <h1 className="text-2xl font-bold">
            LoanLens <span className="text-teal">AI</span>
          </h1>
          <p className="mt-1 text-sm text-slate-500">Kestrel Bank's smart lending assistant</p>
        </div>

        <Card className="p-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="email" className="mb-1 block text-sm font-medium text-navy">
                Email
              </label>
              <input
                id="email"
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-teal focus:ring-2 focus:ring-teal/20"
                placeholder="you@loanlens.com"
              />
            </div>
            <div>
              <label htmlFor="password" className="mb-1 block text-sm font-medium text-navy">
                Password
              </label>
              <input
                id="password"
                type="password"
                required
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-teal focus:ring-2 focus:ring-teal/20"
                placeholder="••••••••"
              />
            </div>
            <Button type="submit" className="w-full" loading={busy === 'form'} disabled={busy !== null}>
              Log in
            </Button>
          </form>
          <p className="mt-4 text-center text-sm text-slate-500">
            New to Kestrel Bank?{' '}
            <Link to="/signup" className="font-medium text-teal hover:underline">
              Create an account
            </Link>
          </p>

          <div className="my-5 flex items-center gap-3 text-xs text-slate-400">
            <div className="h-px flex-1 bg-slate-200" />
            Demo quick login
            <div className="h-px flex-1 bg-slate-200" />
          </div>

          <div className="space-y-2">
            {QUICK_LOGINS.map(({ label, email: qEmail, password: qPassword, icon: Icon }) => (
              <Button
                key={qEmail}
                variant="secondary"
                className="w-full justify-start"
                loading={busy === qEmail}
                disabled={busy !== null}
                onClick={() => doLogin(qEmail, qPassword, qEmail)}
              >
                {busy !== qEmail && <Icon className="h-4 w-4 text-teal" />}
                {label}
              </Button>
            ))}
          </div>
        </Card>
      </div>
    </div>
  )
}
