import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import Spinner from './components/Spinner'
import { useAuth } from './context/AuthContext'
import { roleHome } from './utils/labels'
import Advisor from './pages/Advisor'
import AnalystQueue from './pages/AnalystQueue'
import AnalystReview from './pages/AnalystReview'
import ApplicationDetail from './pages/ApplicationDetail'
import Apply from './pages/Apply'
import AuditLog from './pages/AuditLog'
import EmiCalculator from './pages/EmiCalculator'
import Login from './pages/Login'
import MyApplications from './pages/MyApplications'
import OfficerApplications from './pages/OfficerApplications'
import PolicyAssistant from './pages/PolicyAssistant'
import Products from './pages/Products'
import Signup from './pages/Signup'

/** "/" sends each role to its own home page. */
function RoleRedirect() {
  const { user, loading } = useAuth()
  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Spinner size="lg" />
      </div>
    )
  }
  return <Navigate to={user ? roleHome(user.role) : '/login'} replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />
      <Route path="/" element={<RoleRedirect />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route element={<ProtectedRoute roles={['CUSTOMER']} />}>
            <Route path="/advisor" element={<Advisor />} />
            <Route path="/products" element={<Products />} />
            <Route path="/emi" element={<EmiCalculator />} />
            <Route path="/apply" element={<Apply />} />
            <Route path="/applications" element={<MyApplications />} />
            <Route path="/applications/:id" element={<ApplicationDetail />} />
          </Route>

          <Route path="/policy" element={<PolicyAssistant />} />

          <Route element={<ProtectedRoute roles={['OFFICER']} />}>
            <Route path="/officer/applications" element={<OfficerApplications />} />
          </Route>

          <Route element={<ProtectedRoute roles={['ANALYST']} />}>
            <Route path="/analyst/queue" element={<AnalystQueue />} />
            <Route path="/analyst/applications/:id" element={<AnalystReview />} />
            <Route path="/audit" element={<AuditLog />} />
          </Route>
        </Route>
      </Route>

      <Route path="*" element={<RoleRedirect />} />
    </Routes>
  )
}
