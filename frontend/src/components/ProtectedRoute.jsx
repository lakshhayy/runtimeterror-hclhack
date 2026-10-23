import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { roleHome } from '../utils/labels'
import Spinner from './Spinner'

/** Guards child routes: not logged in -> /login; wrong role -> that role's home page. */
export default function ProtectedRoute({ roles }) {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Spinner size="lg" />
      </div>
    )
  }
  if (!user) return <Navigate to="/login" replace />
  if (roles && !roles.includes(user.role)) return <Navigate to={roleHome(user.role)} replace />
  return <Outlet />
}
