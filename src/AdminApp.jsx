import { useEffect, useState } from "react";
import {
  Bell,
  CircleAlert,
  Landmark,
  LogOut,
  Megaphone,
  Plus,
  Settings,
  Users,
  WalletCards,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import {
  adminLoanAction,
  adminLoanForcePay,
  adminLoanRepayment,
  adminPaymentAction,
  createAdminNotice,
  generateLoanNotices,
  getAdminAudit,
  getAdminDashboard,
  getAdminLoans,
  getAdminMembers,
  getAdminIssues,
  getAdminPayments,
  getAdminSettings,
  sendAdminSupportReply,
  openRealtimeSocket,
  createAdminIssue,
  resolveAdminIssue,
  updateAdminSettings,
} from "./services/api";
import AdminMemberDirectory from "./AdminMemberDirectory";
import { useAuth } from "./context/AuthContext";

function money(value) {
  return `UGX ${Number(value || 0).toLocaleString("en-UG")}`;
}

function timeGreeting() {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

function isOverdueLoan(loan) {
  const createdAt = new Date(loan.created_at)
  const dueDate = new Date(createdAt)
  dueDate.setFullYear(dueDate.getFullYear() + 1)
  return loan.status !== "Pending" && loan.status !== "Rejected" && Number(loan.outstanding_balance) > 0 && new Date() >= dueDate
}

function AdminToolsContent({ audit }) {
  const [settings, setSettings] = useState(null);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  useEffect(() => {
    getAdminSettings()
      .then((settingsData) => {
        setSettings(settingsData);
      })
      .catch(() => setError("Unable to load settings and audit history."));
  }, []);
  async function saveSettings(event) {
    event.preventDefault();
    setStatus("Saving...");
    setError("");
    try {
      const updated = await updateAdminSettings(settings);
      setSettings(updated);
      setStatus("Settings saved.");
    } catch {
      setError("Unable to save SACCO settings.");
    }
  }
  if (!settings && !error)
    return <p className="admin-empty">Loading system controls...</p>;
  return (
    <>
      <section className="admin-section admin-settings-section">
        <div className="admin-section-head">
          <div>
            <span className="eyebrow">System controls</span>
            <h2>SACCO settings</h2>
          </div>
        </div>
        {error && <p className="admin-error">{error}</p>}
        {settings && (
          <form className="settings-form" onSubmit={saveSettings}>
            <label>
              SACCO name
              <input
                value={settings.sacco_name || ""}
                onChange={(event) =>
                  setSettings({ ...settings, sacco_name: event.target.value })
                }
              />
            </label>
            <label>
              MTN number
              <input
                value={settings.mtn_number || ""}
                onChange={(event) =>
                  setSettings({ ...settings, mtn_number: event.target.value })
                }
              />
            </label>
            <label>
              Airtel number
              <input
                value={settings.airtel_number || ""}
                onChange={(event) =>
                  setSettings({
                    ...settings,
                    airtel_number: event.target.value,
                  })
                }
              />
            </label>
            <label>
              Loan interest rate
              <input
                type="number"
                min="0"
                step="0.01"
                value={settings.loan_interest_rate || ""}
                onChange={(event) =>
                  setSettings({
                    ...settings,
                    loan_interest_rate: event.target.value,
                  })
                }
              />
            </label>
            <label className="settings-wide">
              MTN USSD template
              <input
                value={settings.mtn_ussd_template || ""}
                onChange={(event) =>
                  setSettings({
                    ...settings,
                    mtn_ussd_template: event.target.value,
                  })
                }
              />
            </label>
            <label className="settings-wide">
              Airtel USSD template
              <input
                value={settings.airtel_ussd_template || ""}
                onChange={(event) =>
                  setSettings({
                    ...settings,
                    airtel_ussd_template: event.target.value,
                  })
                }
              />
            </label>
            <div className="settings-footer">
              <small>
                {status || "Changes apply to new member payments and loans."}
              </small>
              <button type="submit">Save settings</button>
            </div>
          </form>
        )}
      </section>
      <section className="admin-section admin-audit-section">
        <div className="admin-section-head">
          <div>
            <span className="eyebrow">Accountability</span>
            <h2>Audit log</h2>
          </div>
        </div>
        <div className="audit-list">
          {audit.length ? (
            audit.map((log) => (
              <div className="audit-row" key={log.id}>
                <span>{log.action.replaceAll("_", " ")}</span>
                <div>
                  <strong>
                    {log.object_type} {log.object_id && `· ${log.object_id}`}
                  </strong>
                  <small>{log.description}</small>
                </div>
                <time>{new Date(log.created_at).toLocaleString("en-UG")}</time>
              </div>
            ))
          ) : (
            <p className="admin-empty">No audit activity yet.</p>
          )}
        </div>
      </section>
    </>
  );
}

function AdminTools({ openIssueCount, audit }) {
  const [settings, setSettings] = useState(null);
  const [status, setStatus] = useState("");
  useEffect(() => {
    getAdminSettings()
      .then(setSettings)
      .catch(() => setStatus("Unable to load WhatsApp settings."));
  }, []);
  useEffect(() => {
    const main = document.querySelector(".admin-main");
    if (!main || document.querySelector(".admin-sidebar")) return undefined;
    const sidebar = document.createElement("aside");
    sidebar.className = "admin-sidebar";
    sidebar.innerHTML =
      '<button type="button" class="admin-sidebar-toggle" aria-label="Toggle sidebar">Menu</button><strong>Workspace</strong><nav>' +
      [
        ["overview", "Overview"],
        ["payments", "Payments"],
        ["members", "Members"],
        ["loans", "Loans"],
        ["notifications", "Notifications"],
        ["my-issues", `My Issues (${openIssueCount})`],
        ["notices", "Notices"],
        ["settings", "Settings"],
        ["audit", "Audit log"],
      ]
        .map(
          ([id, label]) =>
            `<button type="button" data-section="${id}">${label}</button>`,
        )
        .join("") +
      "</nav>";
    main.parentElement.insertBefore(sidebar, main);
    const buttons = sidebar.querySelectorAll("nav button");
    const toggle = sidebar.querySelector(".admin-sidebar-toggle");
    buttons.forEach((button) =>
      button.addEventListener("click", () => {
        main.className = `admin-main admin-view-${button.dataset.section} admin-sidebar-collapsed`;
        sidebar.classList.add("collapsed");
        buttons.forEach((item) =>
          item.classList.toggle("active", item === button),
        );
      }),
    );
    toggle.addEventListener("click", () => {
      sidebar.classList.toggle("collapsed");
      main.classList.toggle("admin-sidebar-collapsed");
    });
    buttons[0].classList.add("active");
    main.classList.add("admin-view-overview");
    return () => sidebar.remove();
  }, [openIssueCount]);
  async function saveWhatsApp(event) {
    event.preventDefault();
    setStatus("Saving...");
    try {
      const updated = await updateAdminSettings(settings);
      setSettings(updated);
      setStatus("WhatsApp group link saved.");
    } catch {
      setStatus("Unable to save WhatsApp group link.");
    }
  }
  return (
    <>
      <AdminToolsContent audit={audit} />
      <section className="admin-section">
        <div className="admin-section-head">
          <div>
            <span className="eyebrow">Member community</span>
            <h2>WhatsApp group</h2>
          </div>
        </div>
        {settings && (
          <form className="settings-form" onSubmit={saveWhatsApp}>
            <label className="settings-wide">
              WhatsApp group link
              <input
                type="url"
                placeholder="https://chat.whatsapp.com/..."
                value={settings.whatsapp_group_link || ""}
                onChange={(event) =>
                  setSettings({
                    ...settings,
                    whatsapp_group_link: event.target.value,
                  })
                }
              />
            </label>
            <div className="settings-footer">
              <small>
                {status ||
                  "This link appears as the WhatsApp icon for members."}
              </small>
              <button type="submit">Save link</button>
            </div>
          </form>
        )}
      </section>
    </>
  );
}

export default function AdminApp() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [payments, setPayments] = useState([]);
  const [loans, setLoans] = useState([]);
  const [adminAudit, setAdminAudit] = useState([]);
  const [issues, setIssues] = useState([]);
  const [members, setMembers] = useState([]);
  const [search, setSearch] = useState("");
  const [notice, setNotice] = useState({ title: "", message: "" });
  const [error, setError] = useState("");
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [selectedNotification, setSelectedNotification] = useState(null);
  const [priorityLoanId, setPriorityLoanId] = useState(null);
  const [readNotificationIds, setReadNotificationIds] = useState(() => {
    try { return new Set(JSON.parse(localStorage.getItem("admin_read_notifications") || "[]")); } catch { return new Set(); }
  });
  const [reply, setReply] = useState("");
  const [replyStatus, setReplyStatus] = useState("");
  useEffect(() => {
    Promise.all([
      getAdminDashboard(),
      getAdminPayments(),
      getAdminMembers(),
      getAdminLoans(),
      getAdminAudit(),
      getAdminIssues(),
    ])
      .then(([dashboard, paymentData, memberData, loanData, auditData, issueData]) => {
        setStats(dashboard);
        setPayments(paymentData.results || paymentData);
        setMembers(memberData);
        setLoans(loanData.results || loanData);
        setAdminAudit(auditData);
        setIssues(issueData);
      })
      .catch(() =>
        setError("Unable to load admin information. Please try again."),
      );
  }, []);
  useEffect(() => {
    const refreshAudit = () => getAdminAudit().then(setAdminAudit).catch(() => {});
    const interval = window.setInterval(refreshAudit, 30000);
    return () => window.clearInterval(interval);
  }, []);
  useEffect(() => {
    let active = true;
    let reconnectTimer;
    let socket;
    const refresh = () => Promise.all([getAdminDashboard(), getAdminPayments(), getAdminMembers(), getAdminLoans(), getAdminAudit(), getAdminIssues()]).then(([dashboard, paymentData, memberData, loanData, auditData, issueData]) => {
      if (!active) return;
      setStats(dashboard); setPayments(paymentData.results || paymentData); setMembers(memberData); setLoans(loanData.results || loanData); setAdminAudit(auditData); setIssues(issueData);
    }).catch(() => {});
    const connect = () => {
      if (!active) return;
      socket = openRealtimeSocket(() => refresh());
      socket.onclose = () => { if (active) reconnectTimer = window.setTimeout(connect, 5000); };
    };
    connect();
    return () => { active = false; window.clearTimeout(reconnectTimer); socket?.close(); };
  }, []);
  useEffect(() => {
    localStorage.setItem("admin_read_notifications", JSON.stringify([...readNotificationIds]));
  }, [readNotificationIds]);
  function signOut() {
    logout();
    navigate("/", { replace: true });
  }
  async function updatePayment(paymentId, action) {
    const reason =
      action === "reject"
        ? window.prompt("Reason for rejecting this payment:")
        : "";
    if (action === "reject" && !reason?.trim()) return;
    try {
      const updated = await adminPaymentAction(paymentId, action, reason);
      setPayments((items) =>
        items.map((payment) => (payment.id === paymentId ? updated : payment)),
      );
    } catch {
      setError("Unable to update this payment.");
    }
  }
  async function updateLoan(loanId, action) {
    const reason =
      action === "reject"
        ? window.prompt("Reason for rejecting this loan:")
        : "";
    if (action === "reject" && !reason?.trim()) return;
    try {
      const updated = await adminLoanAction(loanId, action, reason);
      setLoans((items) =>
        items.map((loan) =>
          loan.id === loanId ? { ...loan, ...updated } : loan,
        ),
      );
    } catch {
      setError("Unable to update this loan.");
    }
  }
  async function recordLoanRepayment(loan) {
    const amount = window.prompt(`Enter the amount cleared for ${loan.member_name} (UGX):`)
    if (amount === null || !amount.trim()) return
    if (!/^\d+(\.\d{1,2})?$/.test(amount.trim()) || Number(amount) <= 0 || Number(amount) > Number(loan.outstanding_balance)) {
      setError("Enter a valid amount that does not exceed the outstanding loan balance.")
      return
    }
    try {
      const updated = await adminLoanRepayment(loan.id, amount.trim())
      setLoans((items) => items.map((item) => item.id === loan.id ? { ...item, ...updated } : item))
    } catch {
      setError("Unable to record the loan repayment.")
    }
  }
  async function forcePayLoan(loan) {
    if (!window.confirm(`Force pay ${loan.member_name}'s full loan balance of ${money(loan.outstanding_balance)} from their savings?`)) return
    try {
      const updated = await adminLoanForcePay(loan.id)
      setLoans((items) => items.map((item) => item.id === loan.id ? { ...item, ...updated } : item))
    } catch {
      setError("Unable to force pay this loan. Check that the member has enough savings.")
    }
  }
  async function publishNotice(event) {
    event.preventDefault();
    try {
      await createAdminNotice({ ...notice, kind: "General" });
      setNotice({ title: "", message: "" });
    } catch {
      setError("Unable to publish the notice.");
    }
  }
  async function sendLoanNotice(kind) {
    try {
      await generateLoanNotices(kind);
    } catch {
      setError("Unable to generate loan notices.");
    }
  }
  if (!user || user.role !== "admin") return null;
  const cards = [
    ["Active members", stats?.members?.active ?? stats?.total_members, Users],
    ["Inactive members", stats?.members?.inactive, Users],
    ["New this month", stats?.members?.new, Users],
    ["Members with loans", stats?.members?.with_loans, Landmark],
    [
      "Total savings",
      money(stats?.savings?.total ?? stats?.total_savings),
      WalletCards,
    ],
    ["Savings today", money(stats?.savings?.today), WalletCards],
    ["Savings this month", money(stats?.savings?.month), WalletCards],
    [
      "Average savings",
      money(
        stats?.savings?.total && stats?.members?.total
          ? stats.savings.total / stats.members.total
          : 0,
      ),
      WalletCards,
    ],
    [
      "Loans issued",
      money(stats?.loans?.issued ?? stats?.total_loans),
      Landmark,
    ],
    [
      "Outstanding loans",
      money(stats?.loans?.outstanding ?? stats?.outstanding_loans),
      Landmark,
    ],
    ["Pending applications", stats?.loans?.pending, CircleAlert],
    [
      "Pending payments",
      stats?.payments?.pending ?? stats?.pending_payments,
      CircleAlert,
    ],
    ["Verified payments", stats?.payments?.verified, CircleAlert],
    ["Failed payments", stats?.payments?.failed, CircleAlert],
    ["Duplicate payments", stats?.payments?.duplicate, CircleAlert],
  ];
  const adminNotifications = [
    ...loans.filter(isOverdueLoan).map((loan) => ({
      id: `overdue-${loan.id}`,
      title: "Loan overdue for force payment",
      detail: `${loan.member_name || "Member"} · ${money(loan.outstanding_balance)}`,
      loanId: loan.id,
      createdAt: loan.created_at,
    })),
    ...adminAudit.filter((log) => log.action === "loan_application_submitted" || log.action === "support_message_received" || log.action === "member_withdrawal_approved").map((log) => ({
      id: `audit-${log.id}`,
      title: log.action === "loan_application_submitted" ? "New loan request" : log.action === "support_message_received" ? "New support message" : "Withdrawal approved by member",
      detail: log.description,
      support: log.action === "support_message_received",
      userId: log.action === "support_message_received" ? log.object_id : null,
      loanId: log.action === "loan_application_submitted" ? log.object_id : null,
      createdAt: log.created_at,
    })),
    ...payments.filter((payment) => payment.status === "Pending").map((payment) => ({
      id: `payment-${payment.id}`,
      title: "Payment awaiting review",
      detail: `${payment.internal_reference} · ${money(payment.amount)}`,
      createdAt: payment.created_at,
    })),
    ...loans.filter((loan) => loan.status === "Pending").map((loan) => ({
      id: `loan-${loan.id}`,
      title: "Loan application awaiting review",
      detail: `${loan.member_name || "Member"} · ${money(loan.loan_amount)}`,
      loanId: loan.id,
      createdAt: loan.created_at,
    })),
  ];
  const allAdminNotifications = [...adminNotifications].sort((first, second) => new Date(second.createdAt || 0) - new Date(first.createdAt || 0));
  const unreadNotifications = adminNotifications.filter((item) => !readNotificationIds.has(item.id));
  function openNotification(item) {
    markNotificationRead(item.id);
    if (item.loanId) {
      setPriorityLoanId(item.loanId);
      setNotificationsOpen(false);
      setSelectedNotification(null);
      document.querySelector('.admin-sidebar nav button[data-section="loans"]')?.click();
      return;
    }
    setSelectedNotification(item);
    setReplyStatus("");
  }
  function markNotificationRead(notificationId) {
    setReadNotificationIds((ids) => new Set(ids).add(notificationId));
  }
  async function submitReply(event) {
    event.preventDefault();
    if (!reply.trim() || !selectedNotification?.userId) return;
    setReplyStatus("Sending...");
    try {
      const result = await sendAdminSupportReply(selectedNotification.userId, reply.trim());
      setReply("");
      setReplyStatus(result.message);
    } catch {
      setReplyStatus("Unable to send the reply.");
    }
  }
  async function createIssue() {
    if (!selectedNotification?.userId) return;
    try {
      await createAdminIssue(selectedNotification.userId, selectedNotification.detail);
      setIssues(await getAdminIssues());
      setReplyStatus("Issue added to My Issues.");
    } catch {
      setReplyStatus("Unable to create the issue.");
    }
  }
  async function resolveIssue(issue) {
    if (issue.status === "Resolved") {
      window.alert(issue.report || "No resolution report was recorded.");
      return;
    }
    const report = window.prompt("Write a simple resolution report:");
    if (!report?.trim()) return;
    try {
      const updated = await resolveAdminIssue(issue.id, report.trim());
      setIssues((items) => items.map((item) => item.id === issue.id ? { ...item, ...updated } : item));
    } catch {
      setError("Unable to resolve this issue.");
    }
  }
  return (
    <div className="admin-shell">
      <header className="admin-header">
        <div className="admin-brand">
          <span className="auth-brand-mark">
            <Landmark size={20} />
          </span>
          <div>
            <strong>Coins and Dreams</strong>
            <small>Admin module</small>
          </div>
        </div>
        <div className="admin-header-actions">
          <div className="admin-notification-wrap">
            <button className="admin-icon-button admin-notification-button" type="button" aria-label="Open notifications" title="Notifications" onClick={() => setNotificationsOpen((open) => !open)}>
              <Bell size={18} />
              {unreadNotifications.length > 0 && <span className="admin-notification-count">{unreadNotifications.length > 9 ? "9+" : unreadNotifications.length}</span>}
            </button>
            {notificationsOpen && <div className="admin-notification-panel"><div className="admin-notification-panel-head"><strong>Notifications</strong><span>{unreadNotifications.length ? `${unreadNotifications.length} unread` : "All caught up"}</span></div>{unreadNotifications.length ? unreadNotifications.map((item) => <button className="admin-notification-item" type="button" key={item.id} onClick={() => openNotification(item)}><strong>{item.title}</strong><small>{item.detail}</small></button>) : <p className="admin-empty">No pending reviews.</p>}{selectedNotification && <div className="admin-notification-detail"><strong>{selectedNotification.title}</strong><p>{selectedNotification.detail}</p>{selectedNotification.support && <><div className="admin-notification-detail-actions"><button type="button" onClick={() => setReplyStatus("Reply below")}>Reply</button><button type="button" onClick={createIssue}>Issue</button></div><form onSubmit={submitReply}><textarea maxLength="2000" placeholder="Write a reply..." value={reply} onChange={(event) => setReply(event.target.value)} /><button type="submit">Send reply</button></form></>}{replyStatus && <small>{replyStatus}</small>}</div>}</div>}
          </div>
          <button className="admin-logout" type="button" onClick={signOut}>
            <LogOut size={16} /> Logout
          </button>
        </div>
      </header>
      <main className="admin-main">
        <div className="admin-welcome">
          <div>
            <span className="eyebrow">Operations overview</span>
            <h1>{timeGreeting()}, {user.full_name.split(" ")[0]}</h1>
            <p>Monitor members, payments, and SACCO activity.</p>
          </div>
          <span className="admin-avatar">
            {user.full_name.slice(0, 2).toUpperCase()}
          </span>
        </div>
        {error && <p className="admin-error">{error}</p>}
        <section className="admin-stat-grid">
          {cards.map(([label, value, Icon]) => (
            <article className="admin-stat-card" key={label}>
              <span>
                <Icon size={17} />
              </span>
              <small>{label}</small>
              <strong>{stats ? value : "..."}</strong>
            </article>
          ))}
        </section>
        <section className="admin-section admin-notifications-section">
          <div className="admin-section-head"><div><span className="eyebrow">Activity center</span><h2>Notifications</h2></div><span className="admin-section-description">{allAdminNotifications.length} total</span></div>
          <div className="admin-notifications-list">{allAdminNotifications.filter((item) => !readNotificationIds.has(item.id)).length ? allAdminNotifications.filter((item) => !readNotificationIds.has(item.id)).map((item) => <div className="admin-notification-list-item" role="button" tabIndex="0" key={item.id} onClick={() => openNotification(item)} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") openNotification(item); }}><span className="admin-notification-list-icon"><Bell size={15} /></span><span><strong>{item.title}<em className="admin-new-badge">New</em></strong><small>{item.detail}</small></span><time>{item.createdAt ? new Date(item.createdAt).toLocaleString("en-UG") : ""}</time><button type="button" className="admin-read-button" onClick={(event) => { event.stopPropagation(); markNotificationRead(item.id); }}>Read</button></div>) : <p className="admin-empty">No notifications yet.</p>}</div>
        </section>
        <section className="admin-section admin-issues-section">
          <div className="admin-section-head"><div><span className="eyebrow">Support follow-up</span><h2>My Issues</h2></div><span className="admin-section-description">{issues.filter((issue) => issue.status !== "Resolved").length} open</span></div>
          <div className="admin-issues-list">{issues.length ? issues.map((issue) => <div className={`admin-issue-row ${issue.status === "Resolved" ? "resolved" : ""}`} key={issue.id}><div><strong>{issue.member_name}</strong><small>{issue.description}</small>{issue.status === "Resolved" && <p>{issue.report}</p>}</div><button type="button" onClick={() => resolveIssue(issue)}>{issue.status === "Resolved" ? "Review" : "Resolve"}</button></div>) : <p className="admin-empty">No issues yet.</p>}</div>
        </section>
        <section className="admin-section admin-payments-section">
          <div className="admin-section-head">
            <div>
              <span className="eyebrow">Reconciliation queue</span>
              <h2>Payment monitoring</h2>
            </div>
            <button
              type="button"
              className="admin-icon-button"
              aria-label="Settings"
            >
              <Settings size={18} />
            </button>
          </div>
          <div className="admin-table">
            {payments.length ? (
              payments.map((payment) => (
                <div className="admin-payment" key={payment.id}>
                  <span
                    className={`provider-chip ${payment.provider.toLowerCase()}`}
                  >
                    {payment.provider}
                  </span>
                  <div>
                    <strong>{payment.internal_reference}</strong>
                    <small>
                      {payment.transaction_id || "Awaiting transaction ID"}
                    </small>
                  </div>
                  <div className="admin-payment-right">
                    <strong>{money(payment.amount)}</strong>
                    <span
                      className={`status-chip ${payment.status.toLowerCase()}`}
                    >
                      {payment.status}
                    </span>
                    {payment.status === "Pending" && (
                      <div className="admin-payment-actions">
                        <button
                          type="button"
                          onClick={() => updatePayment(payment.id, "verify")}
                        >
                          Verify
                        </button>
                        <button
                          type="button"
                          onClick={() => updatePayment(payment.id, "reject")}
                        >
                          Reject
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              ))
            ) : (
              <p className="admin-empty">No payments to monitor.</p>
            )}
          </div>
        </section>
        <AdminMemberDirectory
          members={members}
          setMembers={setMembers}
          search={search}
          setSearch={setSearch}
          setError={setError}
        />
        <section className="admin-section admin-loans-section">
          <div className="admin-section-head">
            <div>
              <span className="eyebrow">Credit portfolio</span>
              <h2>Loans</h2>
            </div>
            <div className="notice-actions">
              <button type="button" className="reminder-action" onClick={() => sendLoanNotice("Reminder")}>
                <Bell size={14} />
                Send reminders
              </button>
              <button type="button" className="demand-action" onClick={() => sendLoanNotice("Demand")}>
                <CircleAlert size={14} />
                Send demands
              </button>
            </div>
          </div>
          <div className="admin-member-list">
            {loans.length ? (
              [...loans].sort((first, second) => (String(first.id) === String(priorityLoanId) ? -1 : 0) + (String(second.id) === String(priorityLoanId) ? 1 : 0)).map((loan) => (
                <div className={`admin-member ${isOverdueLoan(loan) ? "loan-overdue" : ""}`} key={loan.id}>
                  <span>LN</span>
                  <div>
                    <strong>
                      {loan.member_name} · {money(loan.outstanding_balance)}
                    </strong>
                    <small>
                      {loan.status} · approved balance {money(loan.loan_amount)}
                    </small>
                  </div>
                  {loan.status === "Pending" && (
                    <div className="admin-payment-actions">
                      <button
                        type="button"
                        onClick={() => updateLoan(loan.id, "approve")}
                      >
                        Approve
                      </button>
                      <button
                        type="button"
                        onClick={() => updateLoan(loan.id, "reject")}
                      >
                        Reject
                      </button>
                    </div>
                  )}
                  {loan.status !== "Pending" && loan.status !== "Rejected" && Number(loan.outstanding_balance) > 0 && (
                    <button type="button" className="loan-repayment-button" aria-label={`Record repayment for ${loan.member_name}`} title="Record cleared amount" onClick={() => recordLoanRepayment(loan)}><Plus size={15} /></button>
                  )}
                  {isOverdueLoan(loan) && <button type="button" className="loan-force-pay-button" onClick={() => forcePayLoan(loan)}>Force pay</button>}
                </div>
              ))
            ) : (
              <p className="admin-empty">No loans to review.</p>
            )}
          </div>
        </section>
        <section className="admin-section admin-notices-section notice-composer">
          <div className="admin-section-head">
            <div>
              <span className="eyebrow">Member communications</span>
              <h2>Write a notice</h2>
              <p className="admin-section-description">
                Share an update with every member in the SACCO.
              </p>
            </div>
            <span className="notice-composer-icon">
              <Megaphone size={18} />
            </span>
          </div>
          <form className="notice-form" onSubmit={publishNotice}>
            <label>
              Title
              <input
                required
                placeholder="e.g. Monthly savings meeting"
                value={notice.title}
                onChange={(event) =>
                  setNotice({ ...notice, title: event.target.value })
                }
              />
            </label>
            <label>
              Message
              <textarea
                required
                placeholder="Write a clear update for members"
                value={notice.message}
                onChange={(event) =>
                  setNotice({ ...notice, message: event.target.value })
                }
              />
            </label>
            <div className="notice-form-footer">
              <small>Your notice will appear on members' home screens.</small>
              <button type="submit">
                <Megaphone size={15} /> Publish notice
              </button>
            </div>
          </form>
        </section>
        <AdminTools openIssueCount={issues.filter((issue) => issue.status !== "Resolved").length} audit={adminAudit} />
      </main>
    </div>
  );
}
