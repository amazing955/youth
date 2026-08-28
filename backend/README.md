#Youth SACCO backend

## Setup

```bash
cd backend
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_data
python manage.py runserver
```

The sample member uses UUID `00000000-0000-0000-0000-000000000001`. The React app reads `VITE_API_URL` and `VITE_MEMBER_ID` from the project environment; copy `.env.example` to `.env` when using the seeded record.

API routes are available under `/api/`, including the authenticated `/api/dashboard/me/`, `/api/auth/login/`, `/api/auth/register/`, `/api/members/`, `/api/savings/`, `/api/loans/`, and `/api/transactions/`.

## Savings reminders

Run `python manage.py send_savings_reminders` once per day using cron or a task scheduler. The command notifies active members whose last saving was at least seven days ago, and avoids sending the same reminder more than once in a seven-day period.

Example cron entry:

```cron
0 9 * * * cd /path/to/project/backend && /path/to/project/backend/.venv/bin/python manage.py send_savings_reminders
```
