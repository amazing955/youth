import { useState } from 'react'
import { ArrowLeft, ArrowRight, CheckCircle2, ShieldCheck } from 'lucide-react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { resetPassword } from './services/api'
import { useAuth } from './context/AuthContext'

function AuthShell({ children, eyebrow, title, subtitle }) {
  const navigate = useNavigate()
  return <div className="auth-page"><button className="auth-back" type="button" onClick={() => navigate('/')}><ArrowLeft size={17} /> Back</button><div className="auth-brand"><span className="auth-brand-mark"><ShieldCheck size={21} /></span><span>Coins <b>and Dreams</b></span></div><div className="auth-panel"><span className="eyebrow">{eyebrow}</span><h1>{title}</h1><p>{subtitle}</p>{children}</div></div>
}

export function WelcomePage() {
  const navigate = useNavigate()
  return <div className="auth-page welcome-page"><div className="auth-orbit orbit-top" /><div className="auth-orbit orbit-bottom" /><div className="welcome-content"><div className="auth-brand large"><span className="auth-brand-mark"><ShieldCheck size={27} /></span><span>Coins <b>and Dreams</b></span></div><div className="welcome-symbol"><span><PiggyIcon /></span></div><h1>Small steps.<br /><em>Big possibilities.</em></h1><p>Start building a brighter financial future with a community that believes in your potential.</p><div className="welcome-actions"><button className="auth-primary" type="button" onClick={() => navigate('/register')}>Register <ArrowRight size={18} /></button><button className="auth-secondary" type="button" onClick={() => navigate('/login')}>Login</button></div><span className="welcome-note"><CheckCircle2 size={14} /> Secure savings made for you</span></div></div>
}

function PiggyIcon() { return <span className="piggy-icon">YS</span> }

export function LoginPage() {
  const { login, loading } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ username: '', password: '' })
  const [error, setError] = useState('')
  async function submit(event) {
    event.preventDefault(); setError('')
    try {
      const result = await login(form)
      navigate(result.user.role === 'admin' ? '/admin' : '/app')
    } catch {
      setError('Invalid username or password.')
    }
  }
  return <AuthShell eyebrow="Welcome back" title="Login" subtitle="Access your Coins and Dreams account."><form className="auth-form" onSubmit={submit}>{error && <p className="form-error">{error}</p>}<label>Username<input required value={form.username} onChange={(event) => setForm({ ...form, username: event.target.value })} /></label><label>Password<input required type="password" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} /></label><button className="auth-primary" disabled={loading} type="submit">{loading ? 'Logging in...' : 'Login'} <ArrowRight size={18} /></button></form></AuthShell>
}

export function ResetPasswordPage() {
  const [params] = useSearchParams()
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const navigate = useNavigate()
  async function submit(event) {
    event.preventDefault(); setError(''); setMessage('')
    if (password !== confirmPassword) { setError('Passwords do not match.'); return }
    try { const result = await resetPassword({ uid: params.get('uid'), token: params.get('token'), password }); setMessage(result.message) } catch { setError('This reset link is invalid, expired, or the password is too weak.') }
  }
  return <AuthShell eyebrow="Account security" title="Reset password" subtitle="Create a new password for your Coins and Dreams account."><form className="auth-form" onSubmit={submit}>{message && <p className="profile-success">{message}</p>}{error && <p className="form-error">{error}</p>}<label>New password<input required type="password" minLength="8" value={password} onChange={(event) => setPassword(event.target.value)} /></label><label>Confirm password<input required type="password" minLength="8" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} /></label><button className="auth-primary" type="submit">Reset password</button>{message && <button className="auth-secondary" type="button" onClick={() => navigate('/login')}>Go to login</button>}</form></AuthShell>
}

const initialForm = { first_name: '', last_name: '', username: '', email: '', phone_number: '', date_of_birth: '', gender: '', password: '', confirm_password: '', nin: '', address: '', next_of_kin_name: '', next_of_kin_phone: '' }
export function RegisterPage() {
  const { register, loading } = useAuth(); const navigate = useNavigate(); const [form, setForm] = useState(initialForm); const [errors, setErrors] = useState({}); const [serverError, setServerError] = useState('')
  function update(name, value) { setForm({ ...form, [name]: value }); setErrors({ ...errors, [name]: '' }) }
  function validate() { const next = {}; Object.entries(form).forEach(([key, value]) => { if (!value.trim()) next[key] = 'Required' }); if (form.email && !/^\S+@\S+\.\S+$/.test(form.email)) next.email = 'Enter a valid email.'; if (form.phone_number && !/^\+?[0-9 ()-]{7,}$/.test(form.phone_number)) next.phone_number = 'Enter a valid phone number.'; if (form.password && !/(?=.*[A-Za-z])(?=.*\d).{8,}/.test(form.password)) next.password = 'Use 8+ characters with a letter and number.'; if (form.password !== form.confirm_password) next.confirm_password = 'Passwords do not match.'; return next }
  async function submit(event) { event.preventDefault(); const next = validate(); if (Object.keys(next).length) { setErrors(next); return } setServerError(''); try { await register(form); navigate('/login') } catch (error) { setServerError(error.message === 'Request failed with status 400' ? 'Please check your details and try again.' : 'Unable to register right now. Please try again.') } }
  const fields = [['first_name', 'First Name', 'text'], ['last_name', 'Last Name', 'text'], ['username', 'Username', 'text'], ['email', 'Email', 'email'], ['phone_number', 'Phone Number', 'tel'], ['date_of_birth', 'Date of Birth', 'date'], ['gender', 'Gender', 'select'], ['nin', 'National ID / NIN', 'text'], ['address', 'Address', 'text'], ['next_of_kin_name', 'Next of Kin Name', 'text'], ['next_of_kin_phone', 'Next of Kin Phone Number', 'tel']]
  return <AuthShell eyebrow="Join the community" title="Create account" subtitle="Open your Coins and Dreams account today."><form className="auth-form register-form" onSubmit={submit}>{serverError && <p className="form-error">{serverError}</p>}<div className="form-grid">{fields.map(([name, label, type]) => <label key={name}>{label} <span className="required">*</span>{type === 'select' ? <select required value={form[name]} onChange={(event) => update(name, event.target.value)}><option value="">Select gender</option><option value="Male">Male</option><option value="Female">Female</option></select> : <input type={type} value={form[name]} onChange={(event) => update(name, event.target.value)} />}{errors[name] && <small className="field-error">{errors[name]}</small>}</label>)}</div><div className="form-grid"><label>Password <span className="required">*</span><input type="password" value={form.password} onChange={(event) => update('password', event.target.value)} />{errors.password && <small className="field-error">{errors.password}</small>}</label><label>Confirm Password <span className="required">*</span><input type="password" value={form.confirm_password} onChange={(event) => update('confirm_password', event.target.value)} />{errors.confirm_password && <small className="field-error">{errors.confirm_password}</small>}</label></div><button className="auth-primary" disabled={loading} type="submit">{loading ? 'Creating account...' : 'Create account'} <ArrowRight size={18} /></button></form></AuthShell>
}
