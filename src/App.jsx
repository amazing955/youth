import { useEffect, useRef, useState } from 'react'
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
  Pencil,
  PiggyBank,
  Plus,
  Receipt,
  Settings as SettingsIcon,
  ShieldCheck,
  Target,
  UserRound,
  X,
} from 'lucide-react'
import './App.css'
import { applyForLoan, cancelLoan, changePassword, getDashboard, getLoanTerms, getLoans, getNotifications, getPaymentConfig, getProfile, getTransactions, markNotificationRead, startPayment, updateProfile, uploadProfilePicture } from './services/api'
import { useAuth } from './context/AuthContext'

const quickActions = [
  { label: 'Save Money', icon: PiggyBank },
  { label: 'Apply for Loan', icon: CreditCard },
  { label: 'Set Goal', icon: Target },
  { label: 'View Statement', icon: Receipt },
]

function resolveQuickActionLabel(hasActiveLoan, label) {
  if (label === 'Apply for Loan' && hasActiveLoan) return 'Repay Loan'
  return label
}

const ease = [0.22, 1, 0.36, 1]

function formatCurrency(amount) {
  return `UGX ${Number(amount || 0).toLocaleString('en-UG')}`
}

function timeGreeting() {
  const hour = new Date().getHours()
  if (hour < 12) return 'Good morning'
  if (hour < 18) return 'Good afternoon'
  return 'Good evening'
}

function formatDate(value) {
  return new Intl.DateTimeFormat('en-UG', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}

function normalizeTransaction(transaction) {
  const amount = Number(transaction.amount)
  return { ...transaction, type: transaction.description || transaction.transaction_type, date: formatDate(transaction.created_at), amount: `${amount >= 0 ? '+' : '-'}${formatCurrency(Math.abs(amount))}`, incoming: amount >= 0 }
}

function AppHeader({ member, onProfile, notifications, onNotificationRead, onNotificationSelect, whatsappGroupLink }) {
  const firstName = member?.full_name?.split(' ')[0] || 'Member'
  const initials = member?.full_name?.split(' ').map((name) => name[0]).join('').slice(0, 2) || 'M'
  const [open, setOpen] = useState(false)
  const unreadCount = notifications.filter((notification) => !notification.is_read).length
  function selectNotification(notification) {
    onNotificationSelect(notification)
    onNotificationRead(notification)
    setOpen(false)
  }
  return (
    <header className="app-header">
      <div>
        <p className="greeting">{timeGreeting()}, {firstName} <span aria-hidden="true">👋</span></p>
        <p className="welcome">Welcome back to your SACCO</p>
      </div>
      <div className="header-actions"><button className={`whatsapp-button ${whatsappGroupLink ? '' : 'not-configured'}`} type="button" onClick={() => whatsappGroupLink ? window.open(whatsappGroupLink, '_blank', 'noopener,noreferrer') : window.alert('The SACCO WhatsApp group link has not been configured by the admin yet.')} aria-label="Join the SACCO WhatsApp group" title="Join SACCO WhatsApp group"><span>WA</span></button><div className="notification-wrap"><button className="icon-button notification-button" type="button" onClick={() => setOpen(!open)} aria-label="Open notifications"><Bell size={19} />{unreadCount > 0 && <span className="notification-count">{unreadCount > 9 ? '9+' : unreadCount}</span>}</button>{open && <div className="notification-panel"><div className="notification-panel-head"><strong>Notifications</strong><span>{unreadCount ? `${unreadCount} unread` : 'All caught up'}</span></div>{notifications.length ? notifications.slice(0, 6).map((notification) => <button className={`notification-item ${notification.is_read ? 'read' : ''}`} type="button" key={notification.id} onClick={() => selectNotification(notification)}><strong>{notification.title}</strong><span>{notification.message}</span><small>{new Date(notification.created_at).toLocaleString('en-UG')}</small></button>) : <p className="empty-state">No notifications yet.</p>}</div>}</div><button className="profile-button" type="button" onClick={onProfile} aria-label="Open profile settings">{member?.profile_picture ? <img src={member.profile_picture} alt="" /> : initials}</button></div>
    </header>
  )
}

function SummaryCard({ dashboard, onSave, onActivate }) {
  const inactive = dashboard.member?.is_active === false
  return (
    <motion.section className="summary-card" initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.55, ease }}>
      <div className="summary-top"><span>Current Savings</span><span className={`summary-badge ${inactive ? 'inactive' : ''}`}><PiggyBank size={14} /> {inactive ? 'Activate' : 'Active'}</span></div>
      <strong>{formatCurrency(dashboard.current_savings)}</strong>
      <div className="summary-bottom"><span>Current savings balance</span><ArrowUpRight size={16} /></div>
      <div className="summary-divider" />
      <div className="loan-row"><div><span>Loan Balance</span><strong>{formatCurrency(dashboard.loan_balance)}</strong></div><div className="loan-progress"><span>Active loan</span><div><i /></div></div></div>
      {inactive ? <button className="activate-button" type="button" onClick={onActivate}>Activate account</button> : <button className="save-button" type="button" onClick={onSave}><Plus size={18} /> Save Money</button>}
    </motion.section>
  )
}

function QuickActions({ onSave, onSetGoal, onViewStatement, onApplyLoan, pendingLoan, hasActiveLoan }) {
  return <section className="quick-section"><div className="section-heading"><h2>Quick actions</h2><span>Manage your money</span></div><div className="quick-grid">{quickActions.map(({ label, icon: Icon }) => {
    const actionLabel = resolveQuickActionLabel(hasActiveLoan, label)
    return <button className="quick-action" type="button" key={label} onClick={label === 'Save Money' ? onSave : label === 'Set Goal' ? onSetGoal : label === 'View Statement' ? onViewStatement : label === 'Apply for Loan' ? onApplyLoan : undefined}><span className="quick-icon"><Icon size={19} /></span><span>{label === 'Apply for Loan' && pendingLoan ? 'Pending' : actionLabel}</span></button>
  })}</div></section>
}

function GoalList({ goals, onEdit }) {
  if (!goals.length) return null
  return <section className="goals-section"><div className="section-heading"><h2>Financial goals</h2><span>{goals.length} saved</span></div><div className="goal-list">{goals.map((goal) => <article className="goal-item" key={goal.id}><span className="goal-icon"><Target size={17} /></span><div><strong>{goal.name}</strong><small>Target amount</small></div><b>{formatCurrency(goal.amount)}</b><button className="goal-edit-button" type="button" onClick={() => onEdit(goal)} aria-label={`Edit ${goal.name}`} title="Edit goal"><Pencil size={14} /></button></article>)}</div></section>
}

function RecentActivity({ transactions, onViewAll }) {
  return <section className="recent-section"><div className="section-heading"><h2>Recent transactions</h2><button className="see-all" type="button" onClick={onViewAll}>See all <ChevronRight size={15} /></button></div><div className="transaction-list">{transactions.length ? transactions.slice(0, 3).map((transaction) => <TransactionRow transaction={normalizeTransaction(transaction)} key={transaction.id} />) : <p className="empty-state">No transactions yet.</p>}</div></section>
}

function TransactionRow({ transaction, detailed = false }) {
  return <div className={`transaction-row ${detailed ? 'detailed' : ''}`}><span className={`transaction-icon ${transaction.incoming ? 'incoming' : 'outgoing'}`}>{transaction.incoming ? <ArrowDownLeft size={17} /> : <ArrowUpRight size={17} />}</span><div className="transaction-info"><strong>{transaction.type}</strong><span>{transaction.date}</span></div><div className="transaction-amount"><strong className={transaction.incoming ? 'positive' : 'negative'}>{transaction.amount}</strong>{detailed ? <span className="transaction-status"><Check size={11} /> {transaction.status}</span> : <span>{transaction.status}</span>}</div></div>
}

function NoticeList({ selectedNotification, onClose }) {
  const noticeRef = useRef(null)
  useEffect(() => {
    if (selectedNotification) noticeRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }, [selectedNotification])
  if (!selectedNotification) return null
  return <section className="notice-list-section selected-notification-section" ref={noticeRef}><div className="section-heading"><h2>Selected notification</h2><button className="see-all" type="button" onClick={onClose}>Close</button></div><article className="notice-item"><span className="notice-kind">{selectedNotification.kind}</span><strong>{selectedNotification.title}</strong><p>{selectedNotification.message}</p><small className="notification-full-date">{new Date(selectedNotification.created_at).toLocaleString('en-UG')}</small></article></section>
}

function HomeScreen({ dashboard, notifications, onNotificationRead, onNotificationSelect, selectedNotification, onCloseNotification, whatsappGroupLink, goals, onSetGoal, onEditGoal, onSave, onActivate, onViewAll, onViewStatement, onApplyLoan, pendingLoan, hasActiveLoan }) {
  const reduceMotion = useReducedMotion()
  return <motion.div className="screen home-screen" initial={reduceMotion ? false : { opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} exit={reduceMotion ? undefined : { opacity: 0, x: -10 }} transition={{ duration: 0.3, ease }}><AppHeader member={dashboard.member} notifications={notifications} onNotificationRead={onNotificationRead} onNotificationSelect={onNotificationSelect} whatsappGroupLink={whatsappGroupLink} onProfile={() => {}} /><SummaryCard dashboard={dashboard} onSave={onSave} onActivate={onActivate} /><QuickActions onSave={onSave} onSetGoal={onSetGoal} onViewStatement={onViewStatement} onApplyLoan={onApplyLoan} pendingLoan={pendingLoan} hasActiveLoan={hasActiveLoan} /><GoalList goals={goals} onEdit={onEditGoal} /><RecentActivity transactions={dashboard.recent_transactions} onViewAll={onViewAll} /><NoticeList selectedNotification={selectedNotification} onClose={onCloseNotification} /><div className="security-note"><ShieldCheck size={16} /><span>Your savings are protected and secure</span></div></motion.div>
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

function GoalSheet({ onClose, onGoalSaved, goal }) {
  const [name, setName] = useState(goal?.name || '')
  const [amount, setAmount] = useState(goal?.amount?.toString() || '')
  const [error, setError] = useState('')

  function submit(event) {
    event.preventDefault()
    const value = Number(amount)
    if (!name.trim() || !value || value <= 0) {
      setError('Enter an item name and a target amount greater than zero.')
      return
    }
    onGoalSaved({ id: goal?.id || Date.now(), name: name.trim(), amount: value })
    onClose()
  }

  return <motion.div className="sheet-overlay" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose}><motion.form className="save-sheet goal-sheet" initial={{ y: '100%' }} animate={{ y: 0 }} exit={{ y: '100%' }} transition={{ duration: 0.4, ease }} onClick={(event) => event.stopPropagation()} onSubmit={submit}><div className="sheet-handle" /><div className="sheet-header"><div><span className="eyebrow">Plan ahead</span><h2>{goal ? 'Edit financial goal' : 'Set a financial goal'}</h2><p className="sheet-subtitle">Choose an item and set the amount you want to reach.</p></div><button className="icon-button" type="button" onClick={onClose} aria-label="Close financial goal form"><X size={19} /></button></div><label className="goal-field">Item name<input required placeholder="For example, school fees" value={name} onChange={(event) => setName(event.target.value)} /></label><label className="goal-field">Target amount<div className="amount-input"><span>UGX</span><input required type="number" min="1" step="1000" placeholder="Enter amount" value={amount} onChange={(event) => setAmount(event.target.value)} /></div></label>{error && <p className="profile-error">{error}</p>}<button className="button button-primary continue-button" type="submit">{goal ? 'Update goal' : 'Save goal'}</button><button className="cancel-button" type="button" onClick={onClose}>Cancel</button></motion.form></motion.div>
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

function SaveSheet({ onClose, activationMode = false, loanRepaymentMode = false, maxRepaymentAmount = 0 }) {
  const FALLBACK_PESAPAL_STORE_URL = 'https://store.pesapal.com/youthsacco'
  const [selectedMethod, setSelectedMethod] = useState('PesaPal')
  const [amount, setAmount] = useState(activationMode ? '10000' : '')
  const [phoneNumber, setPhoneNumber] = useState('')
  const [startError, setStartError] = useState('')
  const [fallbackStoreOpen, setFallbackStoreOpen] = useState(false)
  const paymentMethods = [['PesaPal', 'P', 'pesapal']]

  const amountLimit = loanRepaymentMode ? Number(maxRepaymentAmount || 0) : 0
  const amountError = loanRepaymentMode && amount && Number(amount) > amountLimit ? `Repayment cannot exceed UGX ${amountLimit.toLocaleString('en-UG')}.` : ''

  async function beginPayment() {
    setStartError('')
    try {
      const provider = selectedMethod || 'PesaPal'
      const paymentAmount = activationMode ? '10000' : amount
      const purpose = activationMode ? 'account_activation' : loanRepaymentMode ? 'loan_repayment' : 'savings'
      const result = await startPayment({ provider, amount: paymentAmount, purpose, phone_number: phoneNumber })
      const redirectTarget = result.redirect_url || result.ussd_uri
      if (!redirectTarget) {
        throw new Error('No payment redirect available.')
      }
      window.location.href = redirectTarget
    } catch {
      setFallbackStoreOpen(true)
      setStartError('Payment gateway is unavailable. Opening the PesaPal store inside the app.')
    }
  }

  return (
    <motion.div className="sheet-overlay" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose}>
      <motion.div className="save-sheet" initial={{ y: '100%' }} animate={{ y: 0 }} exit={{ y: '100%' }} transition={{ duration: 0.4, ease }} onClick={(event) => event.stopPropagation()}>
        {fallbackStoreOpen ? (
          <>
            <div className="sheet-handle" />
            <div className="sheet-header">
              <div>
                <span className="eyebrow">PesaPal store</span>
                <h2>Continue payment</h2>
                <p className="sheet-subtitle">The payment gateway is unavailable right now, so we opened the PesaPal store inside the app.</p>
              </div>
              <button className="icon-button" type="button" onClick={onClose} aria-label="Close PesaPal store"><X size={19} /></button>
            </div>
            <iframe title="PesaPal store" src={FALLBACK_PESAPAL_STORE_URL} className="fallback-store-iframe" sandbox="allow-scripts allow-same-origin allow-forms allow-popups" />
            {startError && <p className="profile-error">{startError}</p>}
            <button className="cancel-button" type="button" onClick={onClose}>Close</button>
          </>
        ) : (
          <>
            <div className="sheet-handle" />
            <div className="sheet-header">
              <div>
                <span className="eyebrow">{activationMode ? 'Account activation' : loanRepaymentMode ? 'Loan repayment' : 'Save securely'}</span>
                <h2>{activationMode ? 'Activate your account' : loanRepaymentMode ? 'Repay your loan' : 'Choose Payment Method'}</h2>
                <p className="sheet-subtitle">
                  {activationMode
                    ? 'Pay UGX 10,000 once to activate your account. This does not count as savings.'
                    : loanRepaymentMode
                      ? 'Pay part or all of your outstanding loan balance using PesaPal.'
                      : 'Pay securely with PesaPal to continue'}
                </p>
              </div>
              <button className="icon-button" type="button" onClick={onClose} aria-label="Close payment method selection"><X size={19} /></button>
            </div>

            <div className="payment-options">
              {paymentMethods.map(([label, logo, className]) => (
                <button className={`payment-option ${selectedMethod === label ? 'selected' : ''}`} type="button" key={label} onClick={() => setSelectedMethod(label)}>
                  <span className={`provider-logo ${className}`}>{logo}</span>
                  <span className="payment-label">{label}</span>
                  <span className="selection-indicator">{selectedMethod === label ? <Check size={15} /> : null}</span>
                </button>
              ))}
            </div>

            {selectedMethod && (
              <>
                <p className="selected-method" role="status">
                  {activationMode ? 'Activation fee: ' : loanRepaymentMode ? 'Outstanding balance: ' : 'Selected payment method: '}
                  <strong>{activationMode ? 'UGX 10,000' : loanRepaymentMode ? `UGX ${amountLimit.toLocaleString('en-UG')}` : selectedMethod}</strong>
                  {activationMode ? '. This amount is only for account activation and is not added to your savings.' : loanRepaymentMode ? '. You may pay part or all of this balance.' : ''}
                </p>

                <label className="sheet-amount-label" htmlFor="payment-phone">
                  Phone number for PIN confirmation
                </label>
                <div className="amount-input">
                  <span>+ </span>
                  <input
                    id="payment-phone"
                    type="tel"
                    inputMode="tel"
                    placeholder="256700000000"
                    value={phoneNumber}
                    onChange={(event) => setPhoneNumber(event.target.value.replace(/\D/g, ''))}
                  />
                </div>

                <label className="sheet-amount-label" htmlFor="payment-amount">
                  {activationMode ? 'Activation fee' : loanRepaymentMode ? 'Repayment amount' : 'Amount to save'}
                </label>
                <div className="amount-input">
                  <span>UGX</span>
                  <input
                    id="payment-amount"
                    type="number"
                    min={activationMode ? '10000' : '1'}
                    step="1000"
                    max={loanRepaymentMode ? amountLimit : undefined}
                    placeholder={loanRepaymentMode ? 'Enter repayment amount' : activationMode ? '10000' : '0'}
                    value={amount}
                    onChange={(event) => setAmount(event.target.value)}
                  />
                </div>

                {loanRepaymentMode && amountError && <p className="loan-validation">{amountError}</p>}
                {activationMode ? (
                  <p className="selected-method activation-note">This is a one-time activation fee and not part of your savings.</p>
                ) : loanRepaymentMode ? (
                  <p className="selected-method">You can pay part of or your full loan balance.</p>
                ) : (
                  <p className="selected-method">Save securely into your SACCO account.</p>
                )}

                <button className="button button-primary continue-button" type="button" onClick={beginPayment} disabled={!selectedMethod || !phoneNumber || !amount || Number(amount) <= 0 || Boolean(amountError)}>
                  Continue
                </button>
                {startError && <p className="profile-error">{startError}</p>}
              </>
            )}

            {!selectedMethod && <p className="selected-method">Choose a payment method to continue.</p>}
            <button className="cancel-button" type="button" onClick={onClose}>Cancel</button>
          </>
        )}
      </motion.div>
    </motion.div>
  )
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
  const [activationOpen, setActivationOpen] = useState(false)
  const [loanRepaymentOpen, setLoanRepaymentOpen] = useState(false)
  const [loans, setLoans] = useState([])
  const [notifications, setNotifications] = useState([])
  const [whatsappGroupLink, setWhatsappGroupLink] = useState('')
  const [selectedNotification, setSelectedNotification] = useState(null)
  const [goalOpen, setGoalOpen] = useState(false)
  const [editingGoal, setEditingGoal] = useState(null)
  const [goals, setGoals] = useState(() => {
    try { return JSON.parse(localStorage.getItem('sacco_financial_goals') || '[]') } catch { return [] }
  })
  const [statementMode, setStatementMode] = useState(false)
  useEffect(() => {
    let mounted = true
    Promise.all([getDashboard(), getTransactions(), getLoans(), getNotifications(), getPaymentConfig()])
      .then(([dashboardData, transactionData, loanData, notificationData, paymentConfig]) => {
        if (!mounted) return
        setDashboard(dashboardData)
        setTransactions(transactionData.results || transactionData)
        setLoans(loanData.results || loanData)
        setNotifications(notificationData.notifications || [])
        setWhatsappGroupLink(paymentConfig.whatsapp_group_link || '')
      })
      .catch(() => {
        if (mounted) setTransactionError(true)
      })
      .finally(() => mounted && setLoading(false))
    return () => { mounted = false }
  }, [user])

  async function handleNotificationRead(notification) {
    if (!notification.is_read) {
      await markNotificationRead(notification.id)
      setNotifications((items) => items.map((item) => item.id === notification.id ? { ...item, is_read: true } : item))
    }
  }

  function handleGoalSaved(goal) {
    setGoals((items) => {
      const updated = editingGoal ? items.map((item) => item.id === goal.id ? goal : item) : [...items, goal]
      localStorage.setItem('sacco_financial_goals', JSON.stringify(updated))
      return updated
    })
    setEditingGoal(null)
  }

  function openGoalSheet(goal = null) {
    setEditingGoal(goal)
    setGoalOpen(true)
  }

  const settingsScreen = dashboard && (settingsView === 'profile' ? <ProfileScreen onBack={() => setSettingsView('settings')} /> : <SettingsScreen member={dashboard.member} onLogout={logout} onProfile={() => setSettingsView('profile')} onPassword={() => setPasswordOpen(true)} />)
  const pendingLoan = loans.find((loan) => loan.status === 'Pending')
  const activeLoan = loans.find((loan) => loan.status === 'Approved' || loan.status === 'Active')
  const hasActiveLoan = Boolean(activeLoan)
  const handleAccountActivation = () => {
    window.alert('You are required to pay UGX 10,000 to activate your account.')
    setActivationOpen(true)
  }

  const handleLoanAction = () => {
    if (hasActiveLoan) {
      window.alert('You are repaying your current loan. Choose the amount you want to pay and continue using PesaPal.')
      setLoanRepaymentOpen(true)
      return
    }
    setLoanOpen(true)
  }

  const screens = dashboard ? { home: <HomeScreen dashboard={dashboard} notifications={notifications} onNotificationRead={handleNotificationRead} onNotificationSelect={setSelectedNotification} selectedNotification={selectedNotification} onCloseNotification={() => setSelectedNotification(null)} whatsappGroupLink={whatsappGroupLink} goals={goals} onSetGoal={() => openGoalSheet()} onEditGoal={openGoalSheet} onSave={() => setSheetOpen(true)} onActivate={handleAccountActivation} onApplyLoan={handleLoanAction} pendingLoan={pendingLoan} hasActiveLoan={hasActiveLoan} onViewAll={() => { setStatementMode(false); setActiveTab('transactions') }} onViewStatement={() => { setStatementMode(true); setActiveTab('transactions') }} />, transactions: <TransactionsScreen transactions={transactions} loading={loading} error={transactionError} report={statementMode} />, settings: settingsScreen } : null
  return <div className="app-frame"><div className="app-status"><span>● ● ▰</span></div><main className="app-content"><AnimatePresence mode="wait">{loading && !dashboard ? <p className="app-loading">Loading your SACCO information...</p> : transactionError && !dashboard ? <p className="app-error">Unable to load your SACCO information. Please try again.</p> : screens?.[activeTab]}</AnimatePresence></main><BottomNav activeTab={activeTab} setActiveTab={(tab) => { setActiveTab(tab); if (tab === 'settings') setSettingsView('settings'); if (tab === 'transactions') setStatementMode(false) }} /><AnimatePresence>{sheetOpen && <SaveSheet onClose={() => setSheetOpen(false)} />}{activationOpen && <SaveSheet activationMode onClose={() => setActivationOpen(false)} />}{loanRepaymentOpen && <SaveSheet loanRepaymentMode maxRepaymentAmount={Number(activeLoan?.outstanding_balance || 0)} onClose={() => setLoanRepaymentOpen(false)} />}{goalOpen && <GoalSheet goal={editingGoal} onClose={() => { setGoalOpen(false); setEditingGoal(null) }} onGoalSaved={handleGoalSaved} />}{passwordOpen && <PasswordSheet onClose={() => setPasswordOpen(false)} />}{loanOpen && <LoanSheet pendingLoan={pendingLoan} onLoanCreated={(loan) => setLoans((items) => [...items, loan])} onLoanCancelled={() => setLoans((items) => items.filter((loan) => loan.id !== pendingLoan?.id))} onClose={() => setLoanOpen(false)} />}</AnimatePresence></div>
}
