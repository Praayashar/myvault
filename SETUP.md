# MyVault — Complete Setup Guide

---

## ✅ DEPLOYMENT CHECKLIST

Before going live, complete these steps:

- [ ] Push code to GitHub
- [ ] Create Render Web Service
- [ ] Create Render PostgreSQL database
- [ ] Add all environment variables
- [ ] Setup EmailJS (3 keys)
- [ ] Test login and registration
- [ ] Add Papa's profile
- [ ] Add to phone home screen (PWA)

---

## 🚀 Step 1 — Push to GitHub

```bash
cd myvault
git init
git add .
git commit -m "MyVault v1.0"
# Create a new repo on github.com first, then:
git remote add origin https://github.com/YOUR_USERNAME/myvault.git
git push -u origin main
```

---

## 🌐 Step 2 — Deploy on Render.com

1. Go to https://render.com → Sign up free
2. New → **Web Service** → Connect GitHub → select `myvault`
3. Settings:
   - **Name:** myvault
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
4. Click **Create Web Service**

---

## 🗄️ Step 3 — PostgreSQL Database (Free)

1. In Render dashboard → New → **PostgreSQL**
2. Settings:
   - **Name:** myvault-db
   - **Plan:** Free
3. Click **Create Database**
4. Once created → go to database → copy **Internal Database URL**
5. Go to your Web Service → **Environment** → Add:
   - Key: `DATABASE_URL`
   - Value: paste the Internal Database URL

Your data is now permanent — never lost on redeploy!

---

## 🔐 Step 4 — Environment Variables on Render

Go to Web Service → **Environment** → add all of these:

| Key | Value |
|-----|-------|
| `SECRET_KEY` | any random string e.g. `myvault-abc-123-xyz-2024` |
| `DATABASE_URL` | from PostgreSQL (step 3) |
| `EMAILJS_SERVICE_ID` | from EmailJS (step 5) |
| `EMAILJS_TEMPLATE_ID` | monthly report template ID |
| `EMAILJS_REMINDER_TEMPLATE_ID` | renewal reminder template ID |
| `EMAILJS_PUBLIC_KEY` | from EmailJS account |

Click **Save Changes** — Render redeploys automatically.

---

## 📧 Step 5 — EmailJS Setup (Free)

**Create account:**
1. Go to https://emailjs.com → Sign up free (200 emails/month)

**Connect Gmail:**
1. Email Services → Add New Service → Gmail
2. Connect your Gmail account
3. Note the **Service ID** (e.g. `service_abc123`)

**Create Monthly Report Template:**
1. Email Templates → Create New Template
2. Name: `MyVault Monthly Report`
3. To Email: `{{to_email}}`
4. Subject: `MyVault Report — {{month_name}}`
5. Body:
```
Hi {{to_name}},

MyVault Report for {{month_name}}

SUMMARY
Income:       {{monthly_income}}
Expenses:     {{monthly_expense}}
{{balance_label}}:     {{balance}}
Savings Rate: {{savings_rate}}

TOP CATEGORIES
{{top_categories}}

UPCOMING RENEWALS
{{upcoming_renewals}}

— MyVault
```
6. Note **Template ID** (e.g. `template_xyz789`)

**Create Renewal Reminder Template:**
1. Create another template
2. Name: `MyVault Renewal Reminder`
3. To Email: `{{to_email}}`
4. Subject: `🔔 {{sub_name}} renews in 2 days`
5. Body:
```
Hi {{to_name}},

Reminder: {{sub_name}} renews in 2 days.

Amount: {{sub_amount}}
Date:   {{renewal_date}}

Open MyVault to manage it.

— MyVault
```
6. Note its **Template ID**

**Get Public Key:**
1. Account → General → copy **Public Key**

Add all 4 keys to Render environment variables (see Step 4).

---

## 📱 Step 6 — Add to Phone (PWA)

**iPhone Safari:**
1. Open your Render URL in Safari
2. Tap Share (box with arrow) → Add to Home Screen
3. Name it `MyVault` → Add
4. Opens full screen like a native app!

**Android Chrome:**
1. Open in Chrome → tap ⋮ menu → Add to Home Screen → Add

---

## 👨‍👦 Step 7 — Add Papa's Profile

1. Login with your account
2. Settings → Add Family Profile
3. Enter Papa's name + email + password
4. Papa opens the app → logs in with his credentials
5. All data separate — Family View shows combined

---

## 📊 Google Sheets Backup (Optional)

Want to backup your data to Google Sheets?

**Manual backup (easiest):**
1. Go to Reports → Download CSV
2. Open Google Sheets → File → Import → upload CSV
3. Do this monthly — takes 30 seconds

**Auto backup (advanced — add later):**
- Can be added using Google Sheets API + gspread Python library
- Worth doing once you're comfortable with the app

---

## 🔧 Run Locally (for testing)

```bash
cd myvault
pip install -r requirements.txt
python app.py
# Open http://localhost:5000
# Uses SQLite locally — PostgreSQL only on Render
```

---

## 📁 File Structure

```
myvault/
├── app.py                   ← Flask app entry point
├── config.py                ← All settings & env vars
├── models.py                ← 23 database tables
├── scheduler.py             ← Auto email reminders
├── requirements.txt         ← Python packages
├── Procfile                 ← gunicorn start
├── render.yaml              ← Render config
├── SETUP.md                 ← This guide
├── routes/
│   ├── auth.py              ← Login / Register / Logout
│   ├── main.py              ← Dashboard / Quick Add
│   ├── finance.py           ← Expenses / Income / Budget / Calendar
│   ├── bills.py             ← Subscriptions / EMI / Insurance
│   ├── investments.py       ← FD / RD / MF / Goals
│   ├── life.py              ← Vehicle / Health / Home / Gas / Trips
│   ├── vault.py             ← Passwords / Accounts / Documents / Tickets
│   ├── family.py            ← Family View / Notices / Dates
│   ├── ai.py                ← AI Financial Advisor
│   └── reports.py           ← Reports / Export / Email
├── templates/               ← 18 HTML pages
└── static/
    ├── css/style.css        ← Dark Green & White theme
    ├── js/main.js           ← JS + auto email reminders
    └── manifest.json        ← PWA config
```

---

Built with ❤️ — MyVault v1.0
