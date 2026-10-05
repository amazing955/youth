import { useState } from 'react'
import { ArrowLeft, ArrowRight, Plus, Search } from 'lucide-react'
import { addAdminMemberDeposit, adminPasswordReset, blockMember, getAdminMember, getAdminMembers, reverseAdminMemberDeposit, withdrawAdminMember } from './services/api'

function money(value) { return `UGX ${Number(value || 0).toLocaleString('en-UG')}` }

const fields = [
  ['Username', 'username'], ['Phone number', 'phone_number'], ['Email', 'email'],
  ['Date of birth', 'date_of_birth'], ['Gender', 'gender'], ['NIN', 'nin'],
  ['Address', 'address'], ['Next of kin', 'next_of_kin_name'], ['Next of kin phone', 'next_of_kin_phone'],
  ['Date joined', 'date_joined'],
]

export default function AdminMemberDirectory({ members, setMembers, search, setSearch, setError }) {
  const [selected, setSelected] = useState(null)
  const [loading, setLoading] = useState(false)
  const [resetStatus, setResetStatus] = useState('')

  async function searchMembers(event) {
    event.preventDefault()
    try { setMembers(await getAdminMembers(search)) } catch { setError('Unable to search members.') }
  }

  async function selectMember(member) {
    setLoading(true); setResetStatus('')
    try { setSelected(await getAdminMember(member.id)) } catch { setError('Unable to load member details.') } finally { setLoading(false) }
  }

  async function toggleMember(member) {
    try {
      const updated = await blockMember(member.id, member.is_active !== false)
      setMembers((items) => items.map((item) => item.id === member.id ? { ...item, is_active: updated.is_active } : item))
      setSelected((item) => item?.id === member.id ? { ...item, is_active: updated.is_active } : item)
    } catch { setError('Unable to update member access.') }
  }

  async function sendReset() {
    try {
      const result = await adminPasswordReset(selected.id)
      setResetStatus(`${result.message} Reset link: ${result.reset_url}`)
    } catch { setResetStatus('Unable to send the password reset link.') }
  }

  async function addDeposit(member) {
    const amount = window.prompt(`Enter the amount deposited for ${member.full_name} (UGX):`)
    if (amount === null || !amount.trim()) return
    if (!/^\d+(\.\d{1,2})?$/.test(amount.trim()) || Number(amount) <= 0) {
      setError('Enter a valid positive amount with no more than two decimal places.')
      return
    }
    try {
      const updated = await addAdminMemberDeposit(member.id, amount.trim())
      setMembers((items) => items.map((item) => item.id === member.id ? { ...item, savings_balance: updated.new_balance } : item))
      setSelected(await getAdminMember(member.id))
    } catch { setError('Unable to update the member balance.') }
  }

  async function reverseDeposit(deposit) {
    if (!window.confirm(`Reverse the manual deposit of ${money(deposit.amount)} for ${selected.full_name}?`)) return
    try {
      const updated = await reverseAdminMemberDeposit(selected.id, deposit.reference)
      setSelected((item) => ({ ...item, savings_balance: updated.new_balance, manual_deposits: item.manual_deposits.map((entry) => entry.reference === deposit.reference ? { ...entry, reversed: true } : entry) }))
      setMembers((items) => items.map((item) => item.id === selected.id ? { ...item, savings_balance: updated.new_balance } : item))
    } catch { setError('Unable to reverse the manual deposit.') }
  }

  async function withdrawMember(member) {
    const balance = Number(member.savings_balance || 0)
    if (balance <= 0) { setError('This member has no savings balance to withdraw.'); return }
    const withdrawFullBalance = window.confirm(`Withdraw the full balance of ${money(balance)} for ${member.full_name}? Choose Cancel to enter a custom amount.`)
    const amount = withdrawFullBalance ? String(balance) : window.prompt(`Enter the custom withdrawal amount for ${member.full_name} (UGX):`)
    if (amount === null || !amount.trim()) return
    if (!/^\d+(\.\d{1,2})?$/.test(amount.trim()) || Number(amount) <= 0 || Number(amount) > balance) {
      setError(`Enter a valid amount between UGX 0.01 and ${money(balance)}.`)
      return
    }
    try {
      await withdrawAdminMember(member.id, amount.trim())
      const message = `Withdrawal approval request sent to ${member.full_name}. No funds have been withdrawn. The member has 3 minutes to respond.`
      setResetStatus(message)
      window.alert(message)
      if (selected?.id === member.id) setSelected(await getAdminMember(member.id))
    } catch { setError('Unable to withdraw from the member balance.') }
  }

  if (selected) return <section className="admin-section admin-member-detail">
    <div className="admin-section-head"><div><button type="button" className="admin-back-button" onClick={() => setSelected(null)}><ArrowLeft size={15} /> Members</button><span className="eyebrow">Member record</span><h2>{selected.full_name}</h2></div><button type="button" className="member-block-button" onClick={() => toggleMember(selected)}>{selected.is_active === false ? 'Unblock' : 'Block'}</button></div>
    <div className="admin-member-summary"><div><span>Savings balance</span><strong>{money(selected.savings_balance)}</strong></div><div><span>Outstanding loans</span><strong>{money(selected.loan_balance)}</strong></div><div><span>Active loans</span><strong>{selected.active_loan_count ?? selected.loan_count}</strong></div></div>
    <div className="member-meta-grid">{fields.map(([label, key]) => <div key={key}><span>{label}</span><strong>{selected[key] || 'Not provided'}</strong></div>)}</div>
    <div className="admin-detail-actions"><button type="button" className="password-reset-button" onClick={sendReset}>Send reset link</button><button type="button" className="member-withdraw-button" onClick={() => withdrawMember(selected)}>Withdraw funds</button>{resetStatus && <small>{resetStatus}</small>}</div>
    <h3 className="admin-detail-heading">Manual deposits</h3><div className="admin-loan-table">{selected.manual_deposits?.length ? selected.manual_deposits.map((deposit) => <div className="admin-loan-row" key={deposit.reference}><strong>{money(deposit.amount)}</strong><span>{deposit.reversed ? 'Reversed' : 'Manual deposit'}</span><small>{deposit.created_at ? new Date(deposit.created_at).toLocaleString('en-UG') : ''}</small>{!deposit.reversed && <button type="button" className="member-reverse-button" onClick={() => reverseDeposit(deposit)}>Reverse</button>}</div>) : <p className="admin-empty">No manual deposits registered.</p>}</div>
    <h3 className="admin-detail-heading">Loan history</h3><div className="admin-loan-table">{selected.loans?.length ? selected.loans.map((loan) => <div className="admin-loan-row" key={loan.id}><strong>{money(loan.loan_amount)}</strong><span>{loan.status}</span><small>Paid {money(loan.amount_paid)} · Outstanding {money(loan.outstanding_balance)}</small></div>) : <p className="admin-empty">No loans registered.</p>}</div>
  </section>

  return <section className="admin-section admin-members-section"><div className="admin-section-head"><div><span className="eyebrow">Member directory</span><h2>Members</h2></div><form className="admin-search" onSubmit={searchMembers}><Search size={15} /><input placeholder="Search members" value={search} onChange={(event) => setSearch(event.target.value)} /></form></div>{loading ? <p className="admin-empty">Loading member details...</p> : <div className="admin-member-table"><div className="admin-member-table-head"><span>Member</span><span>Username</span><span>Savings balance</span><span>Loan balance</span><span>Status</span><span></span><span></span><span>Withdraw</span></div>{members.length ? members.map((member) => <div className="admin-member-table-row" role="button" tabIndex="0" key={member.id} onClick={() => selectMember(member)} onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') selectMember(member) }}><strong>{member.full_name}</strong><span>{member.username || 'Not provided'}</span><span>{money(member.savings_balance)}</span><span>{money(member.loan_balance)}</span><span className={member.is_active === false ? 'member-inactive' : 'member-active'}>{member.is_active === false ? 'Inactive' : 'Active'}</span><ArrowRight size={16} /><button type="button" className="member-deposit-button" aria-label={`Add deposit for ${member.full_name}`} title="Add manual deposit" onClick={(event) => { event.stopPropagation(); addDeposit(member) }}><Plus size={15} /></button><button type="button" className="member-withdraw-button" aria-label={`Withdraw from ${member.full_name}`} onClick={(event) => { event.stopPropagation(); withdrawMember(member) }}>Withdraw</button></div>) : <p className="admin-empty">No members found.</p>}</div>}</section>
}
