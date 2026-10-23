import { createContext, useContext, useEffect, useState } from 'react'
import client, { TOKEN_KEY } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  // Only wait for /auth/me when there's a saved token to restore.
  const [loading, setLoading] = useState(() => Boolean(localStorage.getItem(TOKEN_KEY)))

  // Restore the session on page refresh.
  useEffect(() => {
    if (!localStorage.getItem(TOKEN_KEY)) return
    client
      .get('/auth/me')
      .then((res) => setUser(res.data))
      .catch(() => localStorage.removeItem(TOKEN_KEY))
      .finally(() => setLoading(false))
  }, [])

  async function login(email, password) {
    const res = await client.post('/auth/login', { email, password })
    localStorage.setItem(TOKEN_KEY, res.data.accessToken)
    setUser(res.data.user)
    return res.data.user
  }

  async function signup(details) {
    const res = await client.post('/auth/signup', details)
    localStorage.setItem(TOKEN_KEY, res.data.accessToken)
    setUser(res.data.user)
    return res.data.user
  }

  function logout() {
    localStorage.removeItem(TOKEN_KEY)
    setUser(null)
  }

  return <AuthContext.Provider value={{ user, loading, login, signup, logout }}>{children}</AuthContext.Provider>
}

export function useAuth() {
  return useContext(AuthContext)
}
