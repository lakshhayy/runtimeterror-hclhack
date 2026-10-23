import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { Landmark } from 'lucide-react'
import { getErrorMessage } from '../api/client'
import Button from '../components/Button'
import Card from '../components/Card'
import { useAuth } from '../context/AuthContext'
import { roleHome } from '../utils/labels'

const SEGMENTS = [
  { value: 'SALARIED', label: 'Salaried' },
  { value: 'SELF_EMPLOYED', label: 'Self-employed' },
  { value: 'STUDENT', label: 'Student' },
]

const inputClass =
  'w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-teal focus:ring-2 focus:ring-teal/20'

function validate(f) {
  if (f.fullName.trim().length < 2) return 'Please enter your full name.'
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(f.email.trim())) return 'Please enter a valid email address.'
  if (f.password.length < 8 || !/[A-Za-z]/.test(f.password) || !/\d/.test(f.password)) {
    return 'Password must be at least 8 characters with a letter and a number.'
  }
  if (f.password !== f.confirm) return 'Passwords do not match.'
  if (!(Number(f.monthlyIncome) > 0)) return 'Please enter your monthly income.'
  if (f.existingEmi !== '' && Number(f.existingEmi) < 0) return 'Existing EMI cannot be negative.'
  return null
}

export default function Signup() {
  const { user, signup } = useAuth()
  const navigate = useNavigate()
  const [busy, setBusy] = useState(false)
  const [form, setForm] = useState({
    fullName: '',
    email: '',
    password: '',
    confirm: '',
    segment: 'SALARIED',
    monthlyIncome: '',
    existingEmi: '0',
  })

  if (user) return <Navigate to={roleHome(user.role)} replace />

  const update = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.value }))

  async function handleSubmit(e) {
    e.preventDefault()
    const error = validate(form)
    if (error) {
      toast.error(error)
      return
    }
    setBusy(true)
    try {
      const u = await signup({
        fullName: form.fullName.trim(),
        email: form.email.trim(),
        password: form.password,
        segment: form.segment,
        monthlyIncome: Number(form.monthlyIncome),
        existingEmi: Number(form.existingEmi || 0),
      })
      toast.success(`Welcome, ${u.fullName}! Your account is ready.`)
      navigate(roleHome(u.role), { replace: true })
    } catch (err) {
      toast.error(getErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-50 to-teal/10 px-4 py-10">
      <div className="w-full max-w-md">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-navy">
            <Landmark className="h-7 w-7 text-teal" />
          </div>
          <h1 className="text-2xl font-bold">Create your account</h1>
          <p className="mt-1 text-sm text-slate-500">Find the right loan with Kestrel Bank's AI assistant</p>
        </div>

        <Card className="p-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="fullName" className="mb-1 block text-sm font-medium text-navy">
                Full name
              </label>
              <input id="fullName" value={form.fullName} onChange={update('fullName')} maxLength={120} autoComplete="name" className={inputClass} />
            </div>
            <div>
              <label htmlFor="email" className="mb-1 block text-sm font-medium text-navy">
                Email
              </label>
              <input id="email" type="email" value={form.email} onChange={update('email')} autoComplete="email" className={inputClass} />
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label htmlFor="password" className="mb-1 block text-sm font-medium text-navy">
                  Password
                </label>
                <input id="password" type="password" value={form.password} onChange={update('password')} autoComplete="new-password" className={inputClass} />
              </div>
              <div>
                <label htmlFor="confirm" className="mb-1 block text-sm font-medium text-navy">
                  Confirm password
                </label>
                <input id="confirm" type="password" value={form.confirm} onChange={update('confirm')} autoComplete="new-password" className={inputClass} />
              </div>
            </div>
            <p className="-mt-2 text-xs text-slate-500">At least 8 characters, with a letter and a number.</p>
            <div>
              <label htmlFor="segment" className="mb-1 block text-sm font-medium text-navy">
                I am
              </label>
              <select id="segment" value={form.segment} onChange={update('segment')} className={`${inputClass} bg-white`}>
                {SEGMENTS.map((s) => (
                  <option key={s.value} value={s.value}>
                    {s.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label htmlFor="monthlyIncome" className="mb-1 block text-sm font-medium text-navy">
                  Monthly income (₹)
                </label>
                <input id="monthlyIncome" type="number" min={1} value={form.monthlyIncome} onChange={update('monthlyIncome')} className={inputClass} />
              </div>
              <div>
                <label htmlFor="existingEmi" className="mb-1 block text-sm font-medium text-navy">
                  Existing EMIs (₹/month)
                </label>
                <input id="existingEmi" type="number" min={0} value={form.existingEmi} onChange={update('existingEmi')} className={inputClass} />
              </div>
            </div>
            <Button type="submit" className="w-full" loading={busy}>
              Create account
            </Button>
          </form>
          <p className="mt-5 text-center text-sm text-slate-500">
            Already have an account?{' '}
            <Link to="/login" className="font-medium text-teal hover:underline">
              Log in
            </Link>
          </p>
        </Card>
        <p className="mt-4 text-center text-xs text-slate-400">
          Customer accounts only. Bank staff accounts are created by an administrator.
        </p>
      </div>
    </div>
  )
}
