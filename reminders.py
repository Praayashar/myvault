"""
MyVault reminder engine.

Collects everything that is coming due across ALL record types and returns one
digest per user. Previously only subscription renewals were covered, and only
on the exact day that happened to be 2 days before renewal - so most reminders
were missed entirely.

Nothing here sends email. The /cron/reminders endpoint hands this output to
Google Apps Script, which does the sending.
"""

from datetime import date, timedelta
from flask import current_app

from models import (
    db, User, Subscription, Insurance, EMI, Vehicle, DocumentVault,
    Investment, ImportantDate, ReminderLog,
)


def _window(lead_days):
    """Due today through `lead_days` ahead - a range, not a single day."""
    today = date.today()
    return today, today + timedelta(days=lead_days)


def _already_sent(record_type, record_id, due_date):
    return db.session.query(
        ReminderLog.query.filter_by(
            record_type=record_type, record_id=record_id, due_date=due_date
        ).exists()
    ).scalar()


def _days_label(due):
    delta = (due - date.today()).days
    if delta <= 0:
        return "today"
    if delta == 1:
        return "tomorrow"
    return f"in {delta} days"


def _rupees(amount):
    try:
        return f"₹{float(amount or 0):,.0f}"
    except (TypeError, ValueError):
        return "₹0"


def _next_emi_due(emi, horizon_end):
    """EMI stores a day-of-month, not a date. Work out the next actual date."""
    if not emi.due_date:
        return None
    today = date.today()
    day = max(1, min(28, int(emi.due_date)))  # clamp: avoids 30 Feb style errors
    candidate = today.replace(day=day)
    if candidate < today:
        # roll into next month
        year = today.year + (1 if today.month == 12 else 0)
        month = 1 if today.month == 12 else today.month + 1
        candidate = date(year, month, day)
    return candidate if candidate <= horizon_end else None


def collect_for_user(user):
    """Return a list of due items for one user, newest deadline first."""
    cfg = current_app.config
    items = []

    def add(record_type, record_id, due, title, detail):
        if not due or _already_sent(record_type, record_id, due):
            return
        items.append({
            'record_type': record_type,
            'record_id': record_id,
            'due_date': due,
            'due_date_str': due.strftime('%d %b %Y'),
            'when': _days_label(due),
            'title': title,
            'detail': detail,
        })

    # --- Subscription renewals -------------------------------------------
    start, end = _window(cfg['LEAD_DAYS_SUBSCRIPTION'])
    for s in Subscription.query.filter(
        Subscription.user_id == user.id,
        Subscription.is_active == True,  # noqa: E712
        Subscription.renewal_date >= start,
        Subscription.renewal_date <= end,
    ).all():
        add('subscription', s.id, s.renewal_date,
            f"{s.name} renews", _rupees(s.amount))

    # --- Insurance premiums ----------------------------------------------
    start, end = _window(cfg['LEAD_DAYS_INSURANCE'])
    for i in Insurance.query.filter(
        Insurance.user_id == user.id,
        Insurance.premium_due_date >= start,
        Insurance.premium_due_date <= end,
    ).all():
        add('insurance', i.id, i.premium_due_date,
            f"{i.provider} {i.type or ''} premium due".replace('  ', ' '),
            _rupees(i.premium_amount))

    # --- EMI instalments --------------------------------------------------
    start, end = _window(cfg['LEAD_DAYS_EMI'])
    for e in EMI.query.filter(
        EMI.user_id == user.id,
        EMI.paid_installments < EMI.total_installments,
    ).all():
        due = _next_emi_due(e, end)
        if due and due >= start:
            remaining = (e.total_installments or 0) - (e.paid_installments or 0)
            add('emi', e.id, due, f"{e.name} EMI due",
                f"{_rupees(e.emi_amount)} · {remaining} instalments left")

    # --- Vehicle papers ---------------------------------------------------
    start, end = _window(cfg['LEAD_DAYS_VEHICLE'])
    for v in Vehicle.query.filter(Vehicle.user_id == user.id).all():
        label = v.name or v.registration_number or 'Vehicle'
        if v.insurance_expiry and start <= v.insurance_expiry <= end:
            add('vehicle_insurance', v.id, v.insurance_expiry,
                f"{label} insurance expires", v.registration_number or '')
        if v.puc_expiry and start <= v.puc_expiry <= end:
            add('vehicle_puc', v.id, v.puc_expiry,
                f"{label} PUC expires", v.registration_number or '')

    # --- Documents --------------------------------------------------------
    start, end = _window(cfg['LEAD_DAYS_DOCUMENT'])
    for d in DocumentVault.query.filter(
        DocumentVault.user_id == user.id,
        DocumentVault.expiry_date >= start,
        DocumentVault.expiry_date <= end,
    ).all():
        add('document', d.id, d.expiry_date,
            f"{d.doc_name} expires", d.doc_type or '')

    # --- FD / RD maturity -------------------------------------------------
    start, end = _window(cfg['LEAD_DAYS_INVESTMENT'])
    for inv in Investment.query.filter(
        Investment.user_id == user.id,
        Investment.is_active == True,  # noqa: E712
        Investment.maturity_date >= start,
        Investment.maturity_date <= end,
    ).all():
        add('investment', inv.id, inv.maturity_date,
            f"{inv.name} ({inv.type}) matures",
            f"{_rupees(inv.maturity_amount or inv.principal)} · {inv.bank_name or ''}".strip(' ·'))

    # --- Home maintenance tasks ------------------------------------------
    from routes.life import HomeTask  # defined there, imported late to avoid cycles
    start, end = _window(cfg['LEAD_DAYS_HOME_TASK'])
    for t in HomeTask.query.filter(
        HomeTask.user_id == user.id,
        HomeTask.next_due >= start,
        HomeTask.next_due <= end,
    ).all():
        add('home_task', t.id, t.next_due, f"{t.title} due",
            t.contact_name or '')

    # --- Birthdays and important dates -----------------------------------
    # These carry their own per-record reminder_days.
    today = date.today()
    for d in ImportantDate.query.filter(ImportantDate.user_id == user.id).all():
        if not d.date:
            continue
        lead = d.reminder_days if d.reminder_days is not None else 3
        if today <= d.date <= today + timedelta(days=lead):
            add('important_date', d.id, d.date,
                f"{d.title} ({d.type or 'Reminder'})", '')

    items.sort(key=lambda x: x['due_date'])
    return items


def collect_all():
    """Build one digest payload per user who has something due."""
    digests = []
    for user in User.query.all():
        if not user.email:
            continue
        items = collect_for_user(user)
        if not items:
            continue

        lines = [f"• {i['title']} — {i['when']} ({i['due_date_str']})"
                 + (f"  {i['detail']}" if i['detail'] else '')
                 for i in items]

        digests.append({
            'user_id': user.id,
            'to_name': user.name,
            'to_email': user.email,
            'count': len(items),
            'subject': (f"MyVault: {len(items)} thing{'s' if len(items) != 1 else ''} "
                        f"coming up"),
            'body_lines': lines,
            'body': "\n".join(lines),
            'items': [
                {k: (v.isoformat() if isinstance(v, date) else v)
                 for k, v in i.items()}
                for i in items
            ],
        })
    return digests


def mark_sent(user_id, items):
    """Record that these reminders went out, so they are not repeated."""
    saved = 0
    for i in items:
        due = i['due_date']
        if isinstance(due, str):
            due = date.fromisoformat(due)
        if _already_sent(i['record_type'], i['record_id'], due):
            continue
        db.session.add(ReminderLog(
            user_id=user_id,
            record_type=i['record_type'],
            record_id=i['record_id'],
            due_date=due,
        ))
        saved += 1
    db.session.commit()
    return saved
