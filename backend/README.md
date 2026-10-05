#Youth SACCO backend

## Setup

For deployments, set `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=false`, `DJANGO_ALLOWED_HOSTS`, and the payment provider credentials in the environment. Provider credentials are intentionally not stored in source control.

Local `runserver` automatically uses development mode. Set `DJANGO_SECRET_KEY` explicitly when running the backend outside local development.

## Push notifications

Push notifications use Firebase Cloud Messaging. For Android, add the Firebase project's `google-services.json` to `android/app/`, then rebuild/sync the Capacitor app. Set `FIREBASE_SERVICE_ACCOUNT_JSON` to the path of the Firebase Admin SDK service-account JSON on the backend host. Never commit either credential file. Authenticated app sessions register their device token at `/api/push-devices/`; calls to `notify_member` deliver the stored notification through FCM as well as the in-app and email channels.

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
