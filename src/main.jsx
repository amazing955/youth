/* eslint-disable react-refresh/only-export-components */
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import './index.css'
import './App.css'
import { LoginPage, RegisterPage, ResetPasswordPage, WelcomePage } from './AuthPages.jsx'
import { SaccoApp } from './App.jsx'
import AdminApp from './AdminApp.jsx'
import { AuthProvider, useAuth } from './context/AuthContext.jsx'

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => navigator.serviceWorker.register('/sw.js'))
}

function ProtectedRoute() {
  const { isAuthenticated } = useAuth()
  return isAuthenticated ? <SaccoApp /> : <Navigate to="/" replace />
}

function AdminRoute() {
  const { isAuthenticated, user } = useAuth()
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return user?.role === 'admin' ? <AdminApp /> : <Navigate to="/app" replace />
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<WelcomePage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/reset-password" element={<ResetPasswordPage />} />
          <Route path="/app" element={<ProtectedRoute />} />
          <Route path="/admin" element={<AdminRoute />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  </StrictMode>,
)
