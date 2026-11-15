# EventSphere

Mobile-friendly venue hire, event booking and digital ticketing for the IT4123
Agent Based Computing practical. Payments are simulated; no card details or
payment gateway are used.

## Run locally

Requires Python 3.11 or newer.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env and set a private SECRET_KEY. Optionally set ADMIN_EMAIL and
# ADMIN_PASSWORD to create the first admin account.
python -m app.init
python -m uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`. The app creates its tables at startup. The
`.env.example` configures the local database as `eventsphere.db` through
`DATABASE_URL`.

## Deploy on Render

1. Commit and push the project to the connected GitHub repository.
2. In Render, create a **Web Service** from that repository and select the
   project root as the root directory.
3. Use `pip install -r requirements.txt` as the build command and
   `uvicorn app.main:app --host 0.0.0.0 --port $PORT` as the start command.
4. Create a PostgreSQL database in the same region and set `DATABASE_URL` on
   the web service to its internal connection URL. Check Render's current plan
   and billing terms before creating resources. Production startup requires
   this URL to point to PostgreSQL; it will not silently use SQLite.
5. Add `APP_ENV=production`, `HTTPS_ONLY=true`, a strong private `SECRET_KEY`,
   `ADMIN_EMAIL`, and `ADMIN_PASSWORD` in the service's environment settings.
   Do not add these values to Git.
6. Deploy, open the generated HTTPS URL, and test registration, login, event
   browsing, booking, hire requests, admin approval, and check-in. The ticket
   QR images are generated in-memory, so they do not depend on a persistent
   web-service disk.

## Environment variables

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | Required database connection. The example uses SQLite locally; use PostgreSQL in production. |
| `SECRET_KEY` | Session signing key. Required when `APP_ENV=production`. |
| `ADMIN_EMAIL` | Optional first-admin email, created by `python -m app.init`. |
| `ADMIN_PASSWORD` | First-admin password; must be at least 8 characters. |
| `APP_ENV` | Set to `production` for deployment. |
| `HTTPS_ONLY` | Set to `true` when the site is served over HTTPS. |

`.env.example` provides local-development defaults. Copy it to `.env` and edit
the local values; `.env` is ignored by Git. Render does not read repository
`.env` files, so configure production values in the Render service's
environment settings. Never commit production secrets. The initial admin is
created from `ADMIN_EMAIL` and
`ADMIN_PASSWORD`; admins can then create staff accounts. Attendees register
through the site.

## Test

```powershell
python -m pytest -q
```

## Agent rules and key decisions

- **VenueAgent:** Rejects invalid intervals and venue slots that overlap
  published events or active hire requests, with a 30-minute turnaround
  buffer. Routine hire is confirmed and priced by duration times hourly rate.
  A conflicting hire proposes available alternative venues/times.
- **BookingAgent:** Rejects invalid categories, quantities outside 1–6,
  unavailable events, ended events and insufficient inventory. Ticket stock is
  decremented with a conditional database update so concurrent requests cannot
  allocate the same last seats. A user cancellation is refunded in full when
  more than 24 hours remain; otherwise the refund is zero. Event cancellation
  gives every confirmed booking a full simulated refund.
- **TicketAgent:** Creates high-entropy ticket codes. Check-in rejects unknown,
  cancelled, used, wrong-event and out-of-window tickets; an atomic update
  admits a ticket only once.
- **WaitlistAgent:** Keeps queue and hold state in the database, offers a
  released seat to the earliest waiting entry, and expires holds in the
  background scheduler every 30 seconds.
- **NotificationAgent:** Listens for bus `INFORM` broadcasts and persists
  notifications for the affected user(s).

Agent communication uses logged JSON messages with sender, receiver,
performative and conversation ID. The admin dashboard displays event sales,
revenue, check-ins, capacity and recent agent messages.
