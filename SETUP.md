# MyVault v2 — Setup Guide

Personal and family money, records and reminders.
Flask · Supabase Postgres · Render · Google Apps Script.

---

## What changed in v2

**Bugs that could not be recovered from**
- A savings goal with a target of `0` saved happily, then crashed the whole
  Investments page with a divide-by-zero on every load — and the delete button
  for that goal was *on* the dead page. Same bug existed on the EMI page with
  `0` instalments. Both are now rejected at the server and guarded in the page.
- Every form failed silently. `if ((await res.json()).success) location.reload();`
  with no else branch meant a failed save did nothing at all — no message, no
  hint. All 30 calls now show a visible error.

**Security**
- `/forgot-password` used to print a working reset link **on screen** to
  whoever typed an email address. Anyone who knew the address could take the
  account. Removed — the admin now sets passwords from Settings.
- Password vault was base64, which is not encryption. Now Fernet, with the key
  held only in `VAULT_KEY`.
- CSRF protection added across the app.
- Login attempts are now rate limited.
- `SECRET_KEY` no longer has a guessable fallback; the app refuses to start without one.

**Reminders — the real change**
- Previously only subscriptions were covered, only on the exact day that was
  2 days before renewal, and only if somebody opened the Dashboard in a browser.
- Now: insurance, EMI, vehicle insurance, PUC, documents, FD/RD maturity, home
  maintenance, birthdays and subscriptions — over a date *range*, sent
  automatically by Google Apps Script whether or not anyone opens the app.

**AI** — moved server-side onto Gemini 2.5 Flash. The old page called an AI
provider from the browser with no API key (it could never work) and shipped the
full financial snapshot to the browser. Both fixed.

**Backups** — Supabase free tier takes none. A weekly Apps Script job now saves
a full JSON backup to your Google Drive.

---

## Step 1 — Make the repository private

`github.com/Praayashar/myvault` is currently **Public**. The app is live, so the
code, including its weaknesses, is readable by anyone.

1. Repo → **Settings** → scroll down → **Change visibility** → Private
2. Check the history of the committed `github-tokens` file. If it ever held a
   real token, **revoke that token now**. (`.gitignore` now excludes it.)
3. In Supabase, check how many rows are in the `users` table. If it is fewer
   than 2, registration is currently open to anyone who finds the URL.

---

## Step 2 — Generate your three keys

Run these locally and keep the output somewhere safe:

```bash
# SECRET_KEY
python -c "import secrets;print(secrets.token_urlsafe(48))"

# VAULT_KEY  <-- KEEP YOUR OWN COPY OF THIS ONE
python -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())"

# CRON_SECRET
python -c "import secrets;print(secrets.token_urlsafe(32))"
```

> **VAULT_KEY is the one that matters.** It encrypts the password vault. If
> Render loses it or you regenerate it, every stored password becomes
> permanently unreadable — the encrypted database is as useless to you as it is
> to an attacker. Keep a copy in your own password manager.

---

## Step 3 — Render environment variables

Render → `myvault` → **Environment**:

| Key | Value |
|-----|-------|
| `SECRET_KEY` | from step 2 |
| `DATABASE_URL` | your Supabase connection string (already set) |
| `VAULT_KEY` | from step 2 |
| `CRON_SECRET` | from step 2 |
| `GEMINI_API_KEY` | your Gemini key |
| `GEMINI_MODEL` | `gemini-2.5-flash` |

Optional, only to change the defaults:
`LEAD_DAYS_SUBSCRIPTION=3`, `LEAD_DAYS_EMI=3`, `LEAD_DAYS_HOME_TASK=3`,
`LEAD_DAYS_INSURANCE=7`, `LEAD_DAYS_VEHICLE=7`, `LEAD_DAYS_DOCUMENT=7`,
`LEAD_DAYS_INVESTMENT=7`, `MAX_LOGIN_ATTEMPTS=8`, `LOGIN_LOCKOUT_MINUTES=15`.

**The app will not start without `SECRET_KEY`.** That is deliberate — the old
fallback let it run on a guessable key, which lets anyone forge a login session.

---

## Step 4 — Deploy

Push to `main`. If Auto-Deploy is on, Render picks it up; otherwise use
**Manual Deploy → Deploy latest commit**.

Watch the logs for these lines:

```
Database tables ready
```

If you see `VAULT_KEY is not set` or `CRON_SECRET is not set`, those features
are off until you add them.

Two new tables, `reminder_log` and `login_attempts`, are created automatically.
Nothing existing is altered, so there is no migration to run and no risk to
your current data.

---

## Step 5 — Convert the old vault entries

The app reads old base64 entries transparently, so nothing breaks — but they
are still stored unencrypted until you convert them.

```bash
python migrate_vault.py            # shows what would change
python migrate_vault.py --apply    # converts them
```

Safe to run twice. Already-encrypted rows are skipped.

---

## Step 6 — Google Apps Script (this is what makes reminders automatic)

About five minutes, and it replaces a paid cron service, a paid email service
and a paid Render instance all at once.

1. Go to **script.google.com** → **New project**, name it `MyVault Reminders`
2. Delete the sample code, paste in all of **`apps_script.gs`**
3. Edit the two lines at the top:
   ```js
   const APP_URL     = 'https://myvault-oq8m.onrender.com';
   const CRON_SECRET = 'the same CRON_SECRET you put in Render';
   ```
4. Save. Then **Run → `runDailyReminders`** once by hand.
   Google asks permission to send email as you — approve it.
   On the "unverified app" warning choose **Advanced → Go to MyVault Reminders**.
5. **Run → `setupTriggers`** once. That creates all three timers:

| Job | When | What it does |
|-----|------|--------------|
| `runDailyReminders` | daily, 9–10 AM IST | one digest email per person |
| `runMonthlyReport` | 1st of the month | last month's summary |
| `runWeeklyBackup` | Sunday night | full JSON backup to Google Drive |

To see what *would* be sent without sending it, run `previewReminders` and open
**Executions** in the sidebar.

### Why Apps Script and not a scheduler inside the app

The Render free instance sleeps when idle, so an in-process scheduler has no
process alive at 9 AM. An external trigger runs the job *and* wakes the
instance — and the database query it makes also stops the free Supabase project
from pausing after a week of inactivity. One free timer solves three problems.

`scheduler.py` has been deleted; it was never called by anything.

### Email limits

`MailApp` on a free Gmail account allows roughly 100 recipients per day
(a Google Workspace account is far higher). Fine for family. Check the current
quota in Google's documentation before relying on it for anything larger, and
note mail arrives **from your own Gmail address** — not suitable for Raw to
Ready client mail.

---

## Step 7 — Set up the family logins

Whoever registers **first becomes the admin**. So:

1. Open the app and register **yourself** first
2. Settings → **+ Add Family Profile** → add your father
3. Passwords must now be at least 8 characters

If he forgets his password: **Settings → Family Profiles → Set password**.
The self-service reset was removed because it gave away accounts.

### Make it comfortable for him

- Settings → turn on **Simple Mode** (larger text and buttons)
- Add to his phone's home screen: Safari → Share → Add to Home Screen,
  or Chrome → ⋮ → Add to Home Screen

---

## Known limits, honestly

- **`/family` shows every user in the database** their monthly income, expenses
  and net worth. Fine within one family; it is not multi-tenant and must not be
  given to anyone outside it.
- **First load after idle takes up to 50 seconds** on the Render free tier. The
  daily Apps Script call keeps it warm most of the time, but after a quiet
  weekend the first tap will be slow.
- **Supabase free takes no backups** of its own. The weekly Apps Script backup
  is your only safety net — check occasionally that the files are appearing in
  Google Drive.
- **The CSV export on the Reports page covers only expenses and income.** It is
  not a backup. Use the Apps Script JSON backup for that.
- Passwords in the backup file are **encrypted**; restoring them needs `VAULT_KEY`.

---

## Run locally

```bash
pip install -r requirements.txt
export SECRET_KEY=anything-for-local
export VAULT_KEY=$(python -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())")
export CRON_SECRET=localtest
python app.py          # http://localhost:5000, uses SQLite
```

---

## File map

```
myvault/
├── app.py                  Flask setup, CSRF, blueprint registration
├── config.py               All settings and env vars
├── models.py               25 tables (+ reminder_log, login_attempts)
├── reminders.py            NEW - collects everything coming due
├── migrate_vault.py        NEW - one-time base64 -> encrypted conversion
├── apps_script.gs          NEW - paste into script.google.com
├── routes/
│   ├── auth.py             Login (rate limited), register, safe reset
│   ├── main.py             Dashboard, quick add, settings, admin reset
│   ├── finance.py          Expenses, income, budget, calendar
│   ├── bills.py            Subscriptions, EMI, insurance
│   ├── investments.py      FD, RD, MF, goals
│   ├── life.py             Vehicle, health, home, gas, trips
│   ├── vault.py            Passwords (encrypted), accounts, documents, tickets
│   ├── family.py           Family view, notices, dates
│   ├── ai.py               Gemini 2.5 Flash, server-side
│   ├── reports.py          Reports, CSV export
│   └── cron.py             NEW - endpoints for Apps Script
├── templates/              18 pages
└── static/
    ├── css/style.css       + error toast, vault search/reveal/copy
    └── js/main.js          + global fetch wrapper (CSRF + error messages)
```

---

MyVault v2
