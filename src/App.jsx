import { useEffect, useState } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import {
  ArrowDownLeft,
  ArrowLeftRight,
  ArrowUpRight,
  Bell,
  Check,
  ChevronRight,
  CircleHelp,
  CreditCard,
  Home as HomeIcon,
  LockKeyhole,
  LogOut,
  Menu,
  PiggyBank,
  Plus,
  Receipt,
  Send,
  Settings as SettingsIcon,
  ShieldCheck,
  UserRound,
  X,
} from 'lucide-react'
import './App.css'
import { applyForLoan, cancelLoan, changePassword, getDashboard, getLoanTerms, getLoans, getNotices, getPaymentConfig, getProfile, getTransactions, startPayment, updateProfile, uploadProfilePicture } from './services/api'
import { useAuth } from './context/AuthContext'

const quickActions = [
  { label: 'Save Money', icon: PiggyBank },
  { label: 'Apply for Loan', icon: CreditCard },
  { label: 'Send Money', icon: Send },
  { label: 'View Statement', icon: Receipt },
]

const ease = [0.22, 1, 0.36, 1]

function formatCurrency(amount) {
  return `UGX ${Number(amount || 0).toLocaleString('en-UG')}`
}

function formatDate(value) {
  return new Intl.DateTimeFormat('en-UG', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}

function normalizeTransaction(transaction) {
  const amount = Number(transaction.amount)
  return { ...transaction, type: transaction.description || transaction.transaction_type, date: formatDate(transaction.created_at), amount: `${amount >= 0 ? '+' : '-'}${formatCurrency(Math.abs(amount))}`, incoming: amount >= 0 }
}

function AppHeader({ member, onProfile }) {
  const firstName = member?.full_name?.split(' ')[0] || 'Member'
  const initials = member?.full_name?.split(' ').map((name) => name[0]).join('').slice(0, 2) || 'M'
  return (
    <header className="app-header">
      <div>
        <p className="greeting">Good morning, {firstName} <span aria-hidden="true">👋</span></p>
        <p className="welcome">Welcome back to your SACCO</p>
      </div>
      <button className="profile-button" type="button" onClick={onProfile} aria-label="Open profile settings">{member?.profile_picture ? <img src={member.profile_picture} alt="" /> : initials}</button>
    </header>
  )
}

function SummaryCard({ dashboard, onSave }) {
  return (
    <motion.section className="summary-card" initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.55, ease }}>
      <div className="summary-top"><span>Current Savings</span><span className="summary-badge"><PiggyBank size={14} /> Active</span></div>
      <strong>{formatCurrency(dashboard.current_savings)}</strong>
      <div className="summary-bottom"><span>Current savings balance</span><ArrowUpRight size={16} /></div>
      <div className="summary-divider" />
      <div className="loan-row"><div><span>Loan Balance</span><strong>{formatCurrency(dashboard.loan_balance)}</strong></div><div className="loan-progress"><span>Active loan</span><div><i /></div></div></div>
      <button className="save-button" type="button" onClick={onSave}><Plus size={18} /> Save Money</button>
    </motion.section>
  )
}

function QuickActions({ onSave, onViewStatement, onApplyLoan, pendingLoan }) {
  return <section className="quick-section"><div className="section-heading"><h2>Quick actions</h2><span>Manage your money</span></div><div className="quick-grid">{quickActions.map(({ label, icon: Icon }) => <button className="quick-action" type="button" key={label} onClick={label === 'Save Money' ? onSave : label === 'View Statement' ? onViewStatement : label === 'Apply for Loan' ? onApplyLoan : undefined}><span className="quick-icon"><Icon size={19} /></span><span>{label === 'Apply for Loan' && pendingLoan ? 'Pending' : label}</span></button>)}</div></section>
}

function RecentActivity({ transactions, onViewAll }) {
  return <section className="recent-section"><div className="section-heading"><h2>Recent transactions</h2><button className="see-all" type="button" onClick={onViewAll}>See all <ChevronRight size={15} /></button></div><div className="transaction-list">{transactions.length ? transactions.slice(0, 3).map((transaction) => <TransactionRow transaction={normalizeTransaction(transaction)} key={transaction.id} />) : <p className="empty-state">No transactions yet.</p>}</div></section>
}

function TransactionRow({ transaction, detailed = false }) {
  return <div className={`transaction-row ${detailed ? 'detailed' : ''}`}><span className={`transaction-icon ${transaction.incoming ? 'incoming' : 'outgoing'}`}>{transaction.incoming ? <ArrowDownLeft size={17} /> : <ArrowUpRight size={17} />}</span><div className="transaction-info"><strong>{transaction.type}</strong><span>{transaction.date}</span></div><div className="transaction-amount"><strong className={transaction.incoming ? 'positive' : 'negative'}>{transaction.amount}</strong>{detailed ? <span className="transaction-status"><Check size={11} /> {transaction.status}</span> : <span>{transaction.status}</span>}</div></div>
}

function NoticeList({ notices }) {
  if (!notices.length) return null
  return <section className="notice-list-section"><div className="section-heading"><h2>Notices</h2><span>From your SACCO</span></div><div className="notice-list">{notices.slice(0, 3).map((notice) => <article className="notice-item" key={notice.id}><span className="notice-kind">{notice.kind}</span><strong>{notice.title}</strong><p>{notice.message}</p></article>)}</div></section>
}

function HomeScreen({ dashboard, notices, onSave, onViewAll, onViewStatement, onApplyLoan, pendingLoan }) {
  const reduceMotion = useReducedMotion()
  return <motion.div className="screen home-screen" initial={reduceMotion ? false : { opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} exit={reduceMotion ? undefined : { opacity: 0, x: -10 }} transition={{ duration: 0.3, ease }}><AppHeader member={dashboard.member} onProfile={() => {}} /><SummaryCard dashboard={dashboard} onSave={onSave} /><QuickActions onSave={onSave} onViewStatement={onViewStatement} onApplyLoan={onApplyLoan} pendingLoan={pendingLoan} /><RecentActivity transactions={dashboard.recent_transactions} onViewAll={onViewAll} /><NoticeList notices={notices} /><div className="security-note"><ShieldCheck size={16} /><span>Your savings are protected and secure</span></div></motion.div>
}

function TransactionsScreen({ transactions, loading, error, report = false }) {
  const reduceMotion = useReducedMotion()
  const total = transactions.reduce((sum, transaction) => sum + Number(transaction.amount), 0)
  const deposits = transactions.filter((transaction) => Number(transaction.amount) > 0).reduce((sum, transaction) => sum + Number(transaction.amount), 0)
  const spending = Math.abs(transactions.filter((transaction) => Number(transaction.amount) < 0).reduce((sum, transaction) => sum + Number(transaction.amount), 0))
  return <motion.div className="screen inner-screen" initial={reduceMotion ? false : { opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} exit={reduceMotion ? undefined : { opacity: 0, x: -10 }} transition={{ duration: 0.3, ease }}><div className="page-title"><div><span className="eyebrow">{report ? 'Financial report' : 'Your activity'}</span><h1>{report ? 'Statement' : 'Transactions'}</h1></div><button className="icon-button" type="button" aria-label="Filter transactions"><Menu size={19} /></button></div>{loading ? <p className="empty-state">Loading transactions...</p> : error ? <p className="error-state">Unable to load your SACCO information. Please try again.</p> : <>{report && <div className="report-cards"><div><span>Money in</span><strong>{formatCurrency(deposits)}</strong></div><div><span>Money out</span><strong>{formatCurrency(spending)}</strong></div></div>}<div className="transaction-total"><span>{report ? 'Net movement' : 'Total activity'}</span><strong>{formatCurrency(total)}</strong><small>{report ? `${transactions.length} recorded transactions` : 'Net movement from your transactions'}</small></div><div className="full-transactions">{transactions.length ? transactions.map((transaction) => <TransactionRow transaction={normalizeTransaction(transaction)} detailed key={transaction.id} />) : <p className="empty-state">No transactions yet.</p>}</div></>}</motion.div>
}

function SettingsScreen({ member, onLogout, onProfile, onPassword }) {
  const reduceMotion = useReducedMotion()
  const options = [[UserRound, 'Profile', member.full_name], [LockKeyhole, 'Security', 'Your account is secure'], [Bell, 'Notifications', 'On'], [ShieldCheck, 'Change PIN', 'Update your PIN'], [CircleHelp, 'Help & Support', 'We are here to help'], [LogOut, 'Logout', '']]
  return <motion.div className="screen inner-screen" initial={reduceMotion ? false : { opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} exit={reduceMotion ? undefined : { opacity: 0, x: -10 }} transition={{ duration: 0.3, ease }}><div className="page-title"><div><span className="eyebrow">Account</span><h1>Settings</h1></div></div><button className="settings-profile" type="button" onClick={onProfile}><span className="profile-large">{member.profile_picture ? <img src={member.profile_picture} alt="" /> : member.full_name.split(' ').map((name) => name[0]).join('').slice(0, 2)}</span><span><strong>{member.full_name}</strong><small>Member ID: {member.id}</small></span><ChevronRight size={18} /></button><div className="settings-list">{options.map(([Icon, label, detail]) => <button className={`setting-row ${label === 'Logout' ? 'logout' : ''}`} type="button" key={label} onClick={label === 'Logout' ? onLogout : label === 'Profile' ? onProfile : label === 'Security' || label === 'Change PIN' ? onPassword : undefined}><span className="setting-icon"><Icon size={18} /></span><span><strong>{label}</strong>{detail && <small>{detail}</small>}</span><ChevronRight size={17} /></button>)}</div></motion.div>
}

function initials(name = 'Member') { return name.split(' ').map((part) => part[0]).join('').slice(0, 2).toUpperCase() }

function ProfileScreen({ onBack }) {
  const reduceMotion = useReducedMotion()
  const [profile, setProfile] = useState(null)
  const [form, setForm] = useState({})
  const [preview, setPreview] = useState('')
  const [file, setFile] = useState(null)
  const [status, setStatus] = useState('')
  const [error, setError] = useState('')
  useEffect(() => { getProfile().then((data) => { setProfile(data); setForm(data) }).catch(() => setError('Unable to load your profile. Please try again.')) }, [])
  function chooseImage(event) { const selected = event.target.files?.[0]; if (!selected) return; if (!selected.type.startsWith('image/')) { setError('Please choose a JPG, PNG, or WEBP image.'); return } setFile(selected); setPreview(URL.createObjectURL(selected)); setStatus('') }
  async function saveImage() { if (!file) return; setStatus('Uploading...'); setError(''); try { const updated = await uploadProfilePicture(file); setProfile(updated); setForm(updated); setPreview(''); setFile(null); setStatus('Profile picture updated.'); } catch { setError('Unable to upload this image. Please use a valid image under 5 MB.') } }
  async function saveProfile(event) { event.preventDefault(); setStatus('Saving...'); setError(''); try { const updated = await updateProfile({ first_name: form.first_name, last_name: form.last_name, email: form.email, phone_number: form.phone_number, date_of_birth: form.date_of_birth, gender: form.gender, address: form.address }); setProfile(updated); setForm(updated); setStatus('Profile updated successfully.'); } catch { setError('Unable to save your profile. Please check your details.') } }
  if (!profile) return <motion.div className="screen inner-screen" initial={reduceMotion ? false : { opacity: 0 }} animate={{ opacity: 1 }}><div className="page-title"><button className="icon-button" type="button" onClick={onBack} aria-label="Back to settings"><ArrowDownLeft size={18} /></button><h1>Profile</h1></div><p className={error ? 'error-state' : 'empty-state'}>{error || 'Loading profile...'}</p></motion.div>
  const image = preview || profile.profile_picture
  return <motion.div className="screen inner-screen profile-screen" initial={reduceMotion ? false : { opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} exit={reduceMotion ? undefined : { opacity: 0, x: -10 }} transition={{ duration: 0.3, ease }}><div className="page-title"><button className="icon-button" type="button" onClick={onBack} aria-label="Back to settings"><ArrowDownLeft size={18} /></button><div><span className="eyebrow">Your account</span><h1>Profile</h1></div></div><div className="profile-hero"><div className="profile-picture-wrap">{image ? <img src={image} alt="Profile" /> : <span>{initials(profile.full_name)}</span>}<label className="camera-button" htmlFor="profile-picture" aria-label="Choose profile picture"><Plus size={15} /><input id="profile-picture" type="file" accept="image/jpeg,image/png,image/webp" onChange={chooseImage} /></label></div><strong>{profile.full_name}</strong><span>@{profile.username}</span>{file && <button className="profile-save-image" type="button" onClick={saveImage}>Save new picture</button>}</div><form className="profile-form" onSubmit={saveProfile}><div className="profile-fields"><label>First name<input value={form.first_name || ''} onChange={(event) => setForm({ ...form, first_name: event.target.value })} /></label><label>Last name<input value={form.last_name || ''} onChange={(event) => setForm({ ...form, last_name: event.target.value })} /></label><label>Email<input type="email" value={form.email || ''} onChange={(event) => setForm({ ...form, email: event.target.value })} /></label><label>Phone number<input value={form.phone_number || ''} onChange={(event) => setForm({ ...form, phone_number: event.target.value })} /></label><label>Date of birth<input type="date" value={form.date_of_birth || ''} onChange={(event) => setForm({ ...form, date_of_birth: event.target.value })} /></label><label>Gender<input value={form.gender || ''} onChange={(event) => setForm({ ...form, gender: event.target.value })} /></label><label className="full-field">Address<input value={form.address || ''} onChange={(event) => setForm({ ...form, address: event.target.value })} /></label></div><div className="profile-readonly"><span>Username <strong>@{profile.username}</strong></span><span>National ID / NIN <strong>{profile.nin || 'Not provided'}</strong></span><span>Date joined <strong>{new Date(profile.date_joined).toLocaleDateString('en-UG')}</strong></span></div>{status && <p className="profile-success">{status}</p>}{error && <p className="profile-error">{error}</p>}<button className="button button-primary profile-submit" type="submit">Save changes</button></form></motion.div>
}

function PasswordSheet({ onClose }) {
  const [form, setForm] = useState({ current_password: '', new_password: '', confirm_password: '' }); const [message, setMessage] = useState(''); const [error, setError] = useState('')
  async function submit(event) { event.preventDefault(); setMessage(''); setError(''); if (form.new_password.length < 8) { setError('Password must be at least 8 characters.'); return } if (form.new_password !== form.confirm_password) { setError('Passwords do not match.'); return } try { const result = await changePassword(form); setMessage(result.message) } catch { setError('Current password is incorrect or the new password is too weak.') } }
  return <motion.div className="sheet-overlay" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose}><motion.form className="save-sheet password-sheet" initial={{ y: '100%' }} animate={{ y: 0 }} exit={{ y: '100%' }} transition={{ duration: 0.4, ease }} onClick={(event) => event.stopPropagation()} onSubmit={submit}><div className="sheet-handle" /><div className="sheet-header"><div><span className="eyebrow">Account security</span><h2>Change Password</h2></div><button className="icon-button" type="button" onClick={onClose} aria-label="Close password form"><X size={19} /></button></div>{[['current_password', 'Current password'], ['new_password', 'New password'], ['confirm_password', 'Confirm new password']].map(([name, label]) => <label className="password-field" key={name}>{label}<input required type="password" value={form[name]} onChange={(event) => setForm({ ...form, [name]: event.target.value })} /></label>)}{message && <p className="profile-success">{message}</p>}{error && <p className="profile-error">{error}</p>}<button className="button button-primary continue-button" type="submit">Change Password</button><button className="cancel-button" type="button" onClick={onClose}>Cancel</button></motion.form></motion.div>
}

function LoanSheet({ onClose, pendingLoan, onLoanCreated, onLoanCancelled }) {
  const [amount, setAmount] = useState('')
  const [terms, setTerms] = useState(null)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  useEffect(() => { getLoanTerms().then(setTerms).catch(() => setError('Unable to load loan terms. Please try again.')) }, [])
  const value = Number(amount || 0)
  const maximum = Number(terms?.maximum_loan_amount || 0)
  const amountError = amount && value > maximum ? `Enter UGX ${maximum.toLocaleString('en-UG')} or less.` : amount && value <= 0 ? 'Enter an amount greater than zero.' : ''
  const interest = terms ? value * Number(terms.interest_rate) / 100 : 0
  async function submit(event) { event.preventDefault(); if (!terms || amountError || !amount) return; setError(''); try { const loan = await applyForLoan(value); onLoanCreated(loan); setMessage('Loan application submitted for admin review.') } catch { setError('Unable to submit your loan application.') } }
  async function cancelPending() { setError(''); try { await cancelLoan(pendingLoan.id); onLoanCancelled(); onClose() } catch { setError('Unable to cancel this application.') } }
  return <motion.div className="sheet-overlay" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose}><motion.form className="save-sheet loan-sheet" initial={{ y: '100%' }} animate={{ y: 0 }} exit={{ y: '100%' }} transition={{ duration: 0.4, ease }} onClick={(event) => event.stopPropagation()} onSubmit={submit}><div className="sheet-handle" /><div className="sheet-header"><div><span className="eyebrow">Credit request</span><h2>{pendingLoan ? 'Loan request' : 'Apply for a loan'}</h2><p className="sheet-subtitle">{pendingLoan ? 'Your application is being processed by the SACCO.' : 'Your savings determine your eligible amount.'}</p></div><button className="icon-button" type="button" onClick={onClose} aria-label="Close loan application"><X size={19} /></button></div>{pendingLoan ? <><div className="pending-loan-card"><span>Status<strong>Pending</strong></span><span>Requested amount<strong>UGX {Number(pendingLoan.loan_amount).toLocaleString('en-UG')}</strong></span><span>Interest<strong>{pendingLoan.interest_rate}%</strong></span></div><p className="selected-method">Your loan request is being reviewed. You can cancel it while it is still pending.</p>{error && <p className="profile-error">{error}</p>}<button className="cancel-loan-button" type="button" onClick={cancelPending}>Cancel loan request</button></> : terms ? <><div className="loan-eligibility"><span>Current savings<strong>UGX {Number(terms.current_savings).toLocaleString('en-UG')}</strong></span><span>Maximum loan<strong>UGX {maximum.toLocaleString('en-UG')}</strong></span></div><label className="sheet-amount-label" htmlFor="loan-amount">Loan amount</label><div className={`amount-input ${amountError ? 'input-error' : ''}`}><span>UGX</span><input id="loan-amount" type="number" min="1" max={maximum} placeholder="Enter amount" value={amount} onChange={(event) => setAmount(event.target.value)} /></div>{amountError && <p className="loan-validation">{amountError} Keep at least UGX 20,000 in savings.</p>}<div className="loan-interest"><span>Interest rate</span><strong>{terms.interest_rate}%</strong><small>Estimated interest: UGX {Math.round(interest).toLocaleString('en-UG')}</small></div>{message && <p className="profile-success">{message}</p>}{error && <p className="profile-error">{error}</p>}<button className="button button-primary continue-button" type="submit" disabled={!amount || Boolean(amountError) || Boolean(message)}>Submit application</button></> : <p className="empty-state">Loading loan terms...</p>}<button className="cancel-button" type="button" onClick={onClose}>Close</button></motion.form></motion.div>
}

function SaveSheet({ onClose }) {
  const [selectedMethod, setSelectedMethod] = useState('')
  const [amount, setAmount] = useState('')
  const [config, setConfig] = useState(null)
  const [startError, setStartError] = useState('')
  const paymentMethods = [['MTN Mobile Money', 'MTN', 'mtn'], ['Airtel Money', 'airtel', 'airtel']]
  useEffect(() => { getPaymentConfig().then(setConfig).catch(() => setStartError('Unable to load SACCO payment settings.')) }, [])
  async function beginPayment() {
    setStartError('')
    try {
      const provider = selectedMethod.startsWith('MTN') ? 'MTN' : 'Airtel'
      const result = await startPayment({ provider, amount })
      window.location.href = result.ussd_uri
    } catch { setStartError('Unable to start this payment. Please try again.') }
  }
  return <motion.div className="sheet-overlay" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose}><motion.div className="save-sheet" initial={{ y: '100%' }} animate={{ y: 0 }} exit={{ y: '100%' }} transition={{ duration: 0.4, ease }} onClick={(event) => event.stopPropagation()}><div className="sheet-handle" /><div className="sheet-header"><div><span className="eyebrow">Save securely</span><h2>Choose Payment Method</h2><p className="sheet-subtitle">Select your mobile money provider to continue</p></div><button className="icon-button" type="button" onClick={onClose} aria-label="Close payment method selection"><X size={19} /></button></div><div className="payment-options">{paymentMethods.map(([label, logo, className]) => <button className={`payment-option ${selectedMethod === label ? 'selected' : ''}`} type="button" key={label} onClick={() => setSelectedMethod(label)}><span className={`provider-logo ${className}`}>{logo}</span><span className="payment-label">{label}</span><span className="selection-indicator">{selectedMethod === label ? <Check size={15} /> : null}</span></button>)}</div>{selectedMethod && <><p className="selected-method" role="status">Selected payment method: <strong>{selectedMethod}</strong></p><label className="sheet-amount-label" htmlFor="payment-amount">Amount to save</label><div className="amount-input"><span>UGX</span><input id="payment-amount" type="number" min="1" placeholder="Enter amount" value={amount} onChange={(event) => setAmount(event.target.value)} /></div><p className="sacco-number">Send to: {config ? (selectedMethod.startsWith('MTN') ? config.mtn_number : config.airtel_number) : 'Loading SACCO number...'}</p><button className="button button-primary continue-button" type="button" disabled={!amount || !config} onClick={beginPayment}>Open mobile money <ArrowUpRight size={17} /></button></>}{startError && <p className="sheet-error">{startError}</p>}<button className="cancel-button" type="button" onClick={onClose}>Cancel</button></motion.div></motion.div>
}

function BottomNav({ activeTab, setActiveTab }) {
  const tabs = [['home', HomeIcon, 'Home'], ['transactions', ArrowLeftRight, 'Transactions'], ['settings', SettingsIcon, 'Settings']]
  return <nav className="bottom-nav" aria-label="Main navigation">{tabs.map(([id, Icon, label]) => <button className={activeTab === id ? 'active' : ''} type="button" onClick={() => setActiveTab(id)} key={id}><span className="nav-icon"><Icon size={20} /></span><span>{label}</span></button>)}</nav>
}

export function SaccoApp() {
  const { user, logout } = useAuth()
  const [activeTab, setActiveTab] = useState('home')
  const [sheetOpen, setSheetOpen] = useState(false)
  const [dashboard, setDashboard] = useState(null)
  const [transactions, setTransactions] = useState([])
  const [loading, setLoading] = useState(true)
  const [transactionError, setTransactionError] = useState(false)
  const [settingsView, setSettingsView] = useState('settings')
  const [passwordOpen, setPasswordOpen] = useState(false)
  const [loanOpen, setLoanOpen] = useState(false)
  const [loans, setLoans] = useState([])
  const [notices, setNotices] = useState([])
  const [statementMode, setStatementMode] = useState(false)
  useEffect(() => {
    let mounted = true
    Promise.all([getDashboard(), getTransactions(), getLoans(), getNotices()])
      .then(([dashboardData, transactionData, loanData, noticeData]) => {
        if (!mounted) return
        setDashboard(dashboardData)
        setTransactions(transactionData.results || transactionData)
        setLoans(loanData.results || loanData)
        setNotices(noticeData)
      })
      .catch(() => {
        if (mounted) setTransactionError(true)
      })
      .finally(() => mounted && setLoading(false))
    return () => { mounted = false }
  }, [user])

  const settingsScreen = dashboard && (settingsView === 'profile' ? <ProfileScreen onBack={() => setSettingsView('settings')} /> : <SettingsScreen member={dashboard.member} onLogout={logout} onProfile={() => setSettingsView('profile')} onPassword={() => setPasswordOpen(true)} />)
  const pendingLoan = loans.find((loan) => loan.status === 'Pending')
  const screens = dashboard ? { home: <HomeScreen dashboard={dashboard} notices={notices} onSave={() => setSheetOpen(true)} onApplyLoan={() => setLoanOpen(true)} pendingLoan={pendingLoan} onViewAll={() => { setStatementMode(false); setActiveTab('transactions') }} onViewStatement={() => { setStatementMode(true); setActiveTab('transactions') }} />, transactions: <TransactionsScreen transactions={transactions} loading={loading} error={transactionError} report={statementMode} />, settings: settingsScreen } : null
    return <div className="app-frame"><div className="app-status"><span>● ● ▰</span></div><main className="app-content"><AnimatePresence mode="wait">{loading && !dashboard ? <p className="app-loading">Loading your SACCO information...</p> : transactionError && !dashboard ? <p className="app-error">Unable to load your SACCO information. Please try again.</p> : screens?.[activeTab]}</AnimatePresence></main><BottomNav activeTab={activeTab} setActiveTab={(tab) => { setActiveTab(tab); if (tab === 'settings') setSettingsView('settings'); if (tab === 'transactions') setStatementMode(false) }} /><AnimatePresence>{sheetOpen && <SaveSheet onClose={() => setSheetOpen(false)} />}{passwordOpen && <PasswordSheet onClose={() => setPasswordOpen(false)} />}{loanOpen && <LoanSheet pendingLoan={pendingLoan} onLoanCreated={(loan) => setLoans((items) => [...items, loan])} onLoanCancelled={() => setLoans((items) => items.filter((loan) => loan.id !== pendingLoan?.id))} onClose={() => setLoanOpen(false)} />}</AnimatePresence></div>
}

