import axios from 'axios'

export const TOKEN_KEY = 'loanlens_token'

const client = axios.create({ baseURL: import.meta.env.VITE_API_URL })

client.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

client.interceptors.response.use(
  (response) => response,
  (error) => {
    const isLogin = error.config?.url?.includes('/auth/login')
    if (error.response?.status === 401 && !isLogin) {
      localStorage.removeItem(TOKEN_KEY)
      if (window.location.pathname !== '/login') window.location.href = '/login'
    }
    return Promise.reject(error)
  },
)

/** Readable message from our standard error body. */
export function getErrorMessage(err) {
  return err?.response?.data?.error?.message || 'Something went wrong. Please try again.'
}

export default client
