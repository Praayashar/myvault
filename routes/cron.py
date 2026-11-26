"""
Endpoints called by Google Apps Script on a daily/weekly timer.

Why this exists instead of APScheduler: the Render free instance sleeps when
idle, so an in-process scheduler has no process alive at 9 AM to run. An
external trigger both runs the job AND wakes the instance - and the database
query it makes also keeps the free Supabase project from pausing.

Every endpoint is protected by CRON_SECRET and is exempt from CSRF (there is
no browser session involved).
"""

import hmac
import logging
from datetime import date, timedelta

from flask import Blueprint, request, jsonify, current_app
from sqlalchemy import func

from models import (
    db, User, Expense, Income, Subscription, Insurance, EMI, Investment,
    SavingsGoal, BudgetLimit, Vehicle, DocumentVault, HealthRecord,
    AccountDirectory, ImportantDate, FamilyNotice, BusinessExpense,
)
import reminders as reminder_engine

logger = logging.getLogger(__name__)
cron = Blueprint('cron', __name__)


def _authorised():
    """Constant-time comparison of the shared secret."""
    secret = current_app.config.get('CRON_SECRET', '')
    if not secret:
        return False
    supplied = request.args.get('key') or request.headers.get('X-Cron-Key', '')
    return hmac.compare_digest(str(supplied), str(secret))


def _deny():
    return jsonify({'success': False, 'message': 'Unauthorised'}), 401


# ---------------------------------------------------------------------------
# Daily reminders
# ---------------------------------------------------------------------------
@cron.route('/cron/reminders', methods=['GET'])
def reminders_due():
    """Apps Script calls this each morning and emails whatever comes back."""
    if not _authorised():
        return _deny()
    try:
        digests = reminder_engine.collect_all()
        return jsonify({'success': True, 'count': len(digests), 'digests': digests})
    except Exception as e:  # never 500 at the cron, it would stop all mail
        logger.exception("reminder collection failed")
        return jsonify({'success': False, 'message': str(e)}), 500


@cron.route('/cron/reminders/sent', methods=['POST'])
def reminders_sent():
    """Apps Script confirms delivery so the same item is not sent twice."""
    if not _authorised():
        return _deny()
    data = request.get_json(silent=True) or {}
    try:
        total = 0
        for digest in data.get('digests', []):
            total += reminder_engine.mark_sent(
                digest.get('user_id'), digest.get('items', [])
            )
        return jsonify({'success': True, 'marked': total})
    except Exception as e:
        logger.exception("marking reminders sent failed")
        return jsonify({'success': False, 'message': str(e)}), 500


# ---------------------------------------------------------------------------
# Monthly report - Apps Script calls this on the 1st
# ---------------------------------------------------------------------------
@cron.route('/cron/monthly-report', methods=['GET'])
def monthly_report():
    if not _authorised():
        return _deny()

    today = date.today()
    last_month_end = today.replace(day=1) - timedelta(days=1)
    month_start = last_month_end.replace(day=1)

    reports = []
    for user in User.query.all():
        if not user.email:
            continue

        exp = db.session.query(func.sum(Expense.amount)).filter(
            Expense.user_id == user.id,
            Expense.date >= month_start, Expense.date <= last_month_end
        ).scalar() or 0
        inc = db.session.query(func.sum(Income.amount)).filter(
            Income.user_id == user.id,
            Income.date >= month_start, Income.date <= last_month_end
        ).scalar() or 0

        cats = db.session.query(
            Expense.category, func.sum(Expense.amount)
        ).filter(
            Expense.user_id == user.id,
            Expense.date >= month_start, Expense.date <= last_month_end
        ).group_by(Expense.category).order_by(func.sum(Expense.amount).desc()).limit(5).all()

        balance = inc - exp
        rate = round((balance / inc * 100), 1) if inc > 0 else 0

        reports.append({
            'user_id': user.id,
            'to_name': user.name,
            'to_email': user.email,
            'month_name': month_start.strftime('%B %Y'),
            'subject': f"MyVault report — {month_start.strftime('%B %Y')}",
            'monthly_income': f"₹{inc:,.0f}",
            'monthly_expense': f"₹{exp:,.0f}",
            'balance': f"₹{abs(balance):,.0f}",
            'balance_label': 'Saved' if balance >= 0 else 'Overspent',
            'savings_rate': f"{rate}%",
            'top_categories': "\n".join(
                f"  {c}: ₹{a:,.0f}" for c, a in cats
            ) or "  No expenses logged",
        })

    return jsonify({'success': True, 'count': len(reports), 'reports': reports})


# ---------------------------------------------------------------------------
# Weekly backup - Supabase free tier takes no backups of its own
# ---------------------------------------------------------------------------
@cron.route('/cron/backup', methods=['GET'])
def backup():
    """Full JSON dump of every table, for Apps Script to save to Google Drive.

    Password vault entries are deliberately exported ENCRYPTED, exactly as
    stored. A backup sitting in Google Drive should not contain readable
    passwords. Restoring them needs VAULT_KEY, which only you hold.
    """
    if not _authorised():
        return _deny()

    def rows(model, fields):
        out = []
        for r in model.query.all():
            item = {}
            for f in fields:
                v = getattr(r, f, None)
                item[f] = v.isoformat() if hasattr(v, 'isoformat') else v
            out.append(item)
        return out

    from routes.life import FuelLog, HomeTask, HomeLog, GasLog, Trip, TripExpense
    from routes.vault import TicketVault, PasswordVault

    data = {
        'exported_at': date.today().isoformat(),
        'note': 'Password vault values are encrypted. VAULT_KEY is required to read them.',
        'users': rows(User, ['id', 'name', 'email', 'role', 'simple_mode', 'created_at']),
        'expenses': rows(Expense, ['id', 'user_id', 'amount', 'category', 'payment_method', 'description', 'notes', 'date']),
        'incomes': rows(Income, ['id', 'user_id', 'amount', 'source', 'description', 'date']),
        'subscriptions': rows(Subscription, ['id', 'user_id', 'name', 'amount', 'billing_cycle', 'renewal_date', 'category', 'is_active', 'notes']),
        'emis': rows(EMI, ['id', 'user_id', 'name', 'total_amount', 'emi_amount', 'total_installments', 'paid_installments', 'due_date', 'start_date', 'notes']),
        'insurance': rows(Insurance, ['id', 'user_id', 'type', 'provider', 'policy_number', 'premium_amount', 'premium_due_date', 'sum_insured', 'nominee', 'notes']),
        'investments': rows(Investment, ['id', 'user_id', 'type', 'name', 'principal', 'interest_rate', 'start_date', 'maturity_date', 'maturity_amount', 'bank_name', 'is_active', 'notes']),
        'savings_goals': rows(SavingsGoal, ['id', 'user_id', 'name', 'target_amount', 'current_amount', 'target_date']),
        'budget_limits': rows(BudgetLimit, ['id', 'user_id', 'category', 'monthly_limit']),
        'vehicles': rows(Vehicle, ['id', 'user_id', 'name', 'registration_number', 'insurance_expiry', 'puc_expiry', 'last_service_date', 'next_service_km', 'current_km', 'notes']),
        'health_records': rows(HealthRecord, ['id', 'user_id', 'record_type', 'title', 'amount', 'date', 'doctor_name', 'notes']),
        'documents': rows(DocumentVault, ['id', 'user_id', 'doc_type', 'doc_name', 'doc_number', 'expiry_date', 'notes']),
        'accounts': rows(AccountDirectory, ['id', 'user_id', 'account_type', 'account_name', 'account_number', 'ifsc_code', 'branch', 'notes']),
        'passwords_encrypted': rows(PasswordVault, ['id', 'user_id', 'app_name', 'category', 'username', 'email', 'password', 'website_url', 'notes']),
        'tickets': rows(TicketVault, ['id', 'user_id', 'title', 'ticket_type', 'booking_ref', 'from_location', 'to_location', 'travel_date', 'amount', 'notes']),
        'business_expenses': rows(BusinessExpense, ['id', 'user_id', 'date', 'vendor_name', 'vendor_gstin', 'invoice_number', 'category', 'taxable_value', 'gst_rate', 'supply_type', 'cgst', 'sgst', 'igst', 'total_amount', 'payment_mode', 'claim_input_credit', 'notes']),
        'important_dates': rows(ImportantDate, ['id', 'user_id', 'title', 'date', 'type', 'reminder_days', 'notes']),
        'family_notices': rows(FamilyNotice, ['id', 'user_id', 'message', 'is_pinned', 'created_at']),
        'fuel_logs': rows(FuelLog, ['id', 'user_id', 'vehicle_id', 'amount', 'litres', 'km_reading', 'date', 'notes']),
        'home_tasks': rows(HomeTask, ['id', 'user_id', 'title', 'frequency_days', 'next_due', 'last_done', 'contact_name', 'contact_phone', 'notes']),
        'home_logs': rows(HomeLog, ['id', 'user_id', 'title', 'amount', 'date', 'notes']),
        'gas_logs': rows(GasLog, ['id', 'user_id', 'amount', 'date', 'notes']),
        'trips': rows(Trip, ['id', 'user_id', 'name', 'destination', 'budget', 'start_date', 'end_date', 'notes']),
        'trip_expenses': rows(TripExpense, ['id', 'trip_id', 'category', 'description', 'amount', 'date']),
    }
    return jsonify(data)


# ---------------------------------------------------------------------------
# Health check - cheap way to keep Render and Supabase awake
# ---------------------------------------------------------------------------
@cron.route('/cron/ping', methods=['GET'])
def ping():
    users = User.query.count()  # touches the DB so Supabase stays active
    return jsonify({'success': True, 'users': users, 'date': date.today().isoformat()})
