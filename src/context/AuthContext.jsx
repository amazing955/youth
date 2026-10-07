/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useMemo, useState } from 'react'
import { loginRequest, registerRequest } from '../services/api'

const AuthContext = createContext(null)
const TOKEN_KEY = 'sacco_auth_token'
const USER_KEY = 'sacco_auth_user'

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => JSON.parse(localStorage.getItem(USER_KEY) || 'null'))
  const [loading, setLoading] = useState(false)

  async function login(credentials) {
    setLoading(true)
    try {
      const result = await loginRequest(credentials)
      localStorage.setItem(TOKEN_KEY, result.token)
      localStorage.setItem(USER_KEY, JSON.stringify(result.user))
      setUser(result.user)
      return result
    } finally {
      setLoading(false)
    }
  }

  async function register(details) {
    setLoading(true)
    try { return await registerRequest(details) } finally { setLoading(false) }
  }

  function logout() {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
    setUser(null)
  }

  const value = useMemo(() => ({ user, loading, isAuthenticated: Boolean(user && localStorage.getItem(TOKEN_KEY)), login, register, logout }), [user, loading])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  return useContext(AuthContext)
}
