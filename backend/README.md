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
