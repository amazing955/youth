import { useEffect, useState } from "react";
import {
  CircleAlert,
  Landmark,
  LogOut,
  Megaphone,
  Settings,
  Users,
  WalletCards,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import {
  adminLoanAction,
  adminPaymentAction,
  createAdminNotice,
  generateLoanNotices,
  getAdminAudit,
  getAdminDashboard,
  getAdminLoans,
  getAdminMembers,
  getAdminPayments,
  getAdminSettings,
  updateAdminSettings,
} from "./services/api";
import AdminMemberDirectory from "./AdminMemberDirectory";
import { useAuth } from "./context/AuthContext";

function money(value) {
  return `UGX ${Number(value || 0).toLocaleString("en-UG")}`;
}

function AdminToolsContent() {
  const [settings, setSettings] = useState(null);
  const [audit, setAudit] = useState([]);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  useEffect(() => {
    Promise.all([getAdminSettings(), getAdminAudit()])
      .then(([settingsData, auditData]) => {
        setSettings(settingsData);
        setAudit(auditData);
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
      <section className="admin-section">
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
      <section className="admin-section">
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

function AdminTools() {
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
  }, []);
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
      <AdminToolsContent />
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
  const [members, setMembers] = useState([]);
  const [search, setSearch] = useState("");
  const [notice, setNotice] = useState({ title: "", message: "" });
  const [error, setError] = useState("");
  useEffect(() => {
    Promise.all([
      getAdminDashboard(),
      getAdminPayments(),
      getAdminMembers(),
      getAdminLoans(),
    ])
      .then(([dashboard, paymentData, memberData, loanData]) => {
        setStats(dashboard);
        setPayments(paymentData.results || paymentData);
        setMembers(memberData);
        setLoans(loanData.results || loanData);
      })
      .catch(() =>
        setError("Unable to load admin information. Please try again."),
      );
  }, []);
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
  return (
    <div className="admin-shell">
      <header className="admin-header">
        <div className="admin-brand">
          <span className="auth-brand-mark">
            <Landmark size={20} />
          </span>
          <div>
            <strong>Youth Savings</strong>
            <small>Admin module</small>
          </div>
        </div>
        <button className="admin-logout" type="button" onClick={signOut}>
          <LogOut size={16} /> Logout
        </button>
      </header>
      <main className="admin-main">
        <div className="admin-welcome">
          <div>
            <span className="eyebrow">Operations overview</span>
            <h1>Good morning, {user.full_name.split(" ")[0]}</h1>
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
        <section className="admin-section">
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
        <section className="admin-section">
          <div className="admin-section-head">
            <div>
              <span className="eyebrow">Credit portfolio</span>
              <h2>Loans</h2>
            </div>
            <div className="notice-actions">
              <button type="button" onClick={() => sendLoanNotice("Reminder")}>
                Send reminders
              </button>
              <button type="button" onClick={() => sendLoanNotice("Demand")}>
                Send demands
              </button>
            </div>
          </div>
          <div className="admin-member-list">
            {loans.length ? (
              loans.map((loan) => (
                <div className="admin-member" key={loan.id}>
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
                </div>
              ))
            ) : (
              <p className="admin-empty">No loans to review.</p>
            )}
          </div>
        </section>
        <section className="admin-section notice-composer">
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
        <AdminTools />
      </main>
    </div>
  );
}
