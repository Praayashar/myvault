from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import date, timedelta
import logging

logger = logging.getLogger(__name__)

def send_renewal_reminders(app):
    """Check subscriptions expiring in 2 days and queue reminder data."""
    with app.app_context():
        from models import db, Subscription, User
        today = date.today()
        reminder_date = today + timedelta(days=2)

        subs = Subscription.query.filter(
            Subscription.renewal_date == reminder_date,
            Subscription.is_active == True,
            Subscription.reminder_sent == False
        ).all()

        reminders = []
        for sub in subs:
            user = User.query.get(sub.user_id)
            if user and user.email:
                reminders.append({
                    'to_name': user.name,
                    'to_email': user.email,
                    'sub_name': sub.name,
                    'sub_amount': f'₹{sub.amount:,.0f}',
                    'renewal_date': sub.renewal_date.strftime('%d %b %Y')
                })
                sub.reminder_sent = True

        db.session.commit()

        if reminders:
            logger.info(f"Queued {len(reminders)} renewal reminders")

        return reminders


def get_monthly_summary(app, user_id):
    """Get monthly summary data for email."""
    with app.app_context():
        from models import db, Expense, Income, Subscription, User
        from sqlalchemy import func
        today = date.today()
        last_month = today.replace(day=1) - timedelta(days=1)
        month_start = last_month.replace(day=1)
        month_end = last_month

        user = User.query.get(user_id)
        if not user:
            return None

        monthly_exp = db.session.query(func.sum(Expense.amount)).filter(
            Expense.user_id == user_id,
            Expense.date >= month_start,
            Expense.date <= month_end
        ).scalar() or 0

        monthly_inc = db.session.query(func.sum(Income.amount)).filter(
            Income.user_id == user_id,
            Income.date >= month_start,
            Income.date <= month_end
        ).scalar() or 0

        category_data = db.session.query(
            Expense.category, func.sum(Expense.amount)
        ).filter(
            Expense.user_id == user_id,
            Expense.date >= month_start,
            Expense.date <= month_end
        ).group_by(Expense.category).order_by(func.sum(Expense.amount).desc()).limit(5).all()

        upcoming = Subscription.query.filter(
            Subscription.user_id == user_id,
            Subscription.renewal_date >= today,
            Subscription.renewal_date <= today + timedelta(days=7),
            Subscription.is_active == True
        ).all()

        balance = monthly_inc - monthly_exp
        savings_rate = round((balance / monthly_inc * 100), 1) if monthly_inc > 0 else 0

        return {
            'to_name': user.name,
            'to_email': user.email,
            'month_name': month_start.strftime('%B %Y'),
            'monthly_income': f'₹{monthly_inc:,.0f}',
            'monthly_expense': f'₹{monthly_exp:,.0f}',
            'balance': f'₹{abs(balance):,.0f}',
            'balance_label': 'Saved' if balance >= 0 else 'Overspent',
            'savings_rate': f'{savings_rate}%',
            'top_categories': '\n'.join(f'{c}: ₹{a:,.0f}' for c, a in category_data) or 'No expenses logged',
            'upcoming_renewals': '\n'.join(f'{s.name}: ₹{s.amount:,.0f} on {s.renewal_date.strftime("%d %b")}' for s in upcoming) or 'None'
        }


def init_scheduler(app):
    """Initialize APScheduler with reminder jobs."""
    scheduler = BackgroundScheduler(timezone='Asia/Kolkata')

    # Daily at 9 AM IST — check subscription renewals
    scheduler.add_job(
        func=lambda: send_renewal_reminders(app),
        trigger=CronTrigger(hour=9, minute=0),
        id='renewal_reminders',
        name='Send renewal reminders',
        replace_existing=True
    )

    scheduler.start()
    logger.info("Scheduler started — renewal reminders active at 9 AM IST")
    return scheduler
