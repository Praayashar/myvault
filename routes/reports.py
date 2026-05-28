from flask import Blueprint, render_template, request, jsonify, make_response
from flask_login import login_required, current_user
from models import db, Expense, Income, Subscription, Investment, EMI, SavingsGoal, BudgetLimit
from datetime import datetime, date, timedelta
from sqlalchemy import func
import calendar
import csv
import io

reports = Blueprint('reports', __name__)

@reports.route('/reports')
@login_required
def index():
    today = date.today()
    year = int(request.args.get('year', today.year))
    month = int(request.args.get('month', today.month))

    month_start = date(year, month, 1)
    month_end = date(year, month, calendar.monthrange(year, month)[1])
    month_name = month_start.strftime('%B %Y')

    # Monthly totals
    monthly_exp = db.session.query(func.sum(Expense.amount)).filter(
        Expense.user_id == current_user.id,
        Expense.date >= month_start, Expense.date <= month_end
    ).scalar() or 0

    monthly_inc = db.session.query(func.sum(Income.amount)).filter(
        Income.user_id == current_user.id,
        Income.date >= month_start, Income.date <= month_end
    ).scalar() or 0

    # Category breakdown
    category_data = db.session.query(
        Expense.category, func.sum(Expense.amount)
    ).filter(
        Expense.user_id == current_user.id,
        Expense.date >= month_start, Expense.date <= month_end
    ).group_by(Expense.category).order_by(func.sum(Expense.amount).desc()).all()

    # Payment method breakdown
    payment_data = db.session.query(
        Expense.payment_method, func.sum(Expense.amount)
    ).filter(
        Expense.user_id == current_user.id,
        Expense.date >= month_start, Expense.date <= month_end
    ).group_by(Expense.payment_method).all()

    # All expenses this month
    expenses = Expense.query.filter(
        Expense.user_id == current_user.id,
        Expense.date >= month_start, Expense.date <= month_end
    ).order_by(Expense.date.desc()).all()

    # All income this month
    incomes = Income.query.filter(
        Income.user_id == current_user.id,
        Income.date >= month_start, Income.date <= month_end
    ).order_by(Income.date.desc()).all()

    # Subscriptions renewed this month
    subs_renewed = Subscription.query.filter(
        Subscription.user_id == current_user.id,
        Subscription.renewal_date >= month_start,
        Subscription.renewal_date <= month_end
    ).all()

    # Budget performance
    budgets = BudgetLimit.query.filter_by(user_id=current_user.id).all()
    budget_perf = []
    for b in budgets:
        spent = db.session.query(func.sum(Expense.amount)).filter(
            Expense.user_id == current_user.id,
            Expense.category == b.category,
            Expense.date >= month_start, Expense.date <= month_end
        ).scalar() or 0
        pct = min((spent / b.monthly_limit * 100), 100) if b.monthly_limit else 0
        budget_perf.append({
            'category': b.category,
            'limit': b.monthly_limit,
            'spent': spent,
            'pct': round(pct),
            'status': 'over' if spent > b.monthly_limit else 'warning' if pct >= 70 else 'good'
        })

    # Yearly overview data (all 12 months of selected year)
    yearly_exp = []
    yearly_inc = []
    month_labels = []
    for m in range(1, 13):
        ms = date(year, m, 1)
        me = date(year, m, calendar.monthrange(year, m)[1])
        exp = db.session.query(func.sum(Expense.amount)).filter(
            Expense.user_id == current_user.id,
            Expense.date >= ms, Expense.date <= me
        ).scalar() or 0
        inc = db.session.query(func.sum(Income.amount)).filter(
            Income.user_id == current_user.id,
            Income.date >= ms, Income.date <= me
        ).scalar() or 0
        yearly_exp.append(round(exp, 2))
        yearly_inc.append(round(inc, 2))
        month_labels.append(ms.strftime('%b'))

    # Smart insights
    insights = generate_insights(
        monthly_exp, monthly_inc, category_data,
        budget_perf, subs_renewed, current_user.id
    )

    # Month navigation
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    return render_template('reports.html',
        today=today, year=year, month=month, month_name=month_name,
        monthly_exp=monthly_exp, monthly_inc=monthly_inc,
        balance=monthly_inc - monthly_exp,
        category_data=category_data, payment_data=payment_data,
        expenses=expenses, incomes=incomes,
        subs_renewed=subs_renewed, budget_perf=budget_perf,
        insights=insights,
        yearly_exp=yearly_exp, yearly_inc=yearly_inc, month_labels=month_labels,
        prev_month=prev_month, prev_year=prev_year,
        next_month=next_month, next_year=next_year
    )


def generate_insights(monthly_exp, monthly_inc, category_data, budget_perf, subs_renewed, user_id):
    insights = []
    today = date.today()

    # Savings rate
    if monthly_inc > 0:
        savings_rate = ((monthly_inc - monthly_exp) / monthly_inc) * 100
        if savings_rate >= 30:
            insights.append({'type': 'success', 'text': f'Excellent! You saved {savings_rate:.0f}% of your income this month. Keep it up!'})
        elif savings_rate >= 10:
            insights.append({'type': 'info', 'text': f'You saved {savings_rate:.0f}% of income. Aim for 30% for stronger financial health.'})
        elif savings_rate >= 0:
            insights.append({'type': 'warning', 'text': f'Low savings rate of {savings_rate:.0f}%. Try reducing top expense categories.'})
        else:
            insights.append({'type': 'danger', 'text': f'Spending exceeded income by ₹{abs(monthly_inc - monthly_exp):,.0f}. Review your expenses urgently.'})

    # Top spending category
    if category_data:
        top_cat, top_amt = category_data[0]
        if monthly_exp > 0:
            pct = (top_amt / monthly_exp) * 100
            if pct > 40:
                insights.append({'type': 'warning', 'text': f'{top_cat} is your biggest expense at {pct:.0f}% of total spending (₹{top_amt:,.0f}). Consider if this can be reduced.'})

    # Over-budget alerts
    over_budget = [b for b in budget_perf if b['status'] == 'over']
    if over_budget:
        cats = ', '.join(b['category'] for b in over_budget)
        insights.append({'type': 'danger', 'text': f'Over budget in: {cats}. Review these categories next month.'})

    # Subscription cost check
    if subs_renewed:
        total_subs = sum(s.amount for s in subs_renewed)
        insights.append({'type': 'info', 'text': f'₹{total_subs:,.0f} spent on {len(subs_renewed)} subscriptions this month. Review if all are being used.'})

    # No income logged
    if monthly_inc == 0:
        insights.append({'type': 'warning', 'text': 'No income logged this month. Add your salary or other income to get accurate savings analysis.'})

    return insights


@reports.route('/reports/export/csv')
@login_required
def export_csv():
    year = int(request.args.get('year', date.today().year))
    month = int(request.args.get('month', date.today().month))
    month_start = date(year, month, 1)
    month_end = date(year, month, calendar.monthrange(year, month)[1])

    output = io.StringIO()
    writer = csv.writer(output)

    # Expenses
    writer.writerow(['=== EXPENSES ==='])
    writer.writerow(['Date', 'Category', 'Description', 'Payment Method', 'Amount (₹)'])
    expenses = Expense.query.filter(
        Expense.user_id == current_user.id,
        Expense.date >= month_start, Expense.date <= month_end
    ).order_by(Expense.date).all()
    for e in expenses:
        writer.writerow([e.date, e.category, e.description or '', e.payment_method, e.amount])

    writer.writerow([])

    # Income
    writer.writerow(['=== INCOME ==='])
    writer.writerow(['Date', 'Source', 'Description', 'Amount (₹)'])
    incomes = Income.query.filter(
        Income.user_id == current_user.id,
        Income.date >= month_start, Income.date <= month_end
    ).order_by(Income.date).all()
    for i in incomes:
        writer.writerow([i.date, i.source, i.description or '', i.amount])

    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = f'attachment; filename=myvault_{year}_{month:02d}.csv'
    response.headers['Content-type'] = 'text/csv'
    return response


@reports.route('/reports/summary/json')
@login_required
def summary_json():
    """Returns monthly summary as JSON for email sending via EmailJS."""
    today = date.today()
    month = int(request.args.get('month', today.month))
    year = int(request.args.get('year', today.year))
    month_start = date(year, month, 1)
    month_end = date(year, month, calendar.monthrange(year, month)[1])

    monthly_exp = db.session.query(func.sum(Expense.amount)).filter(
        Expense.user_id == current_user.id,
        Expense.date >= month_start, Expense.date <= month_end
    ).scalar() or 0

    monthly_inc = db.session.query(func.sum(Income.amount)).filter(
        Income.user_id == current_user.id,
        Income.date >= month_start, Income.date <= month_end
    ).scalar() or 0

    category_data = db.session.query(
        Expense.category, func.sum(Expense.amount)
    ).filter(
        Expense.user_id == current_user.id,
        Expense.date >= month_start, Expense.date <= month_end
    ).group_by(Expense.category).order_by(func.sum(Expense.amount).desc()).all()

    upcoming_renewals = Subscription.query.filter(
        Subscription.user_id == current_user.id,
        Subscription.renewal_date >= today,
        Subscription.renewal_date <= today + timedelta(days=7),
        Subscription.is_active == True
    ).all()

    return jsonify({
        'user_name': current_user.name,
        'user_email': current_user.email,
        'month_name': month_start.strftime('%B %Y'),
        'monthly_income': monthly_inc,
        'monthly_expense': monthly_exp,
        'balance': monthly_inc - monthly_exp,
        'top_categories': [{'name': c, 'amount': a} for c, a in category_data[:5]],
        'upcoming_renewals': [{'name': s.name, 'amount': s.amount, 'date': s.renewal_date.isoformat()} for s in upcoming_renewals],
        'savings_rate': round(((monthly_inc - monthly_exp) / monthly_inc * 100), 1) if monthly_inc > 0 else 0
    })


@reports.route('/reminders/pending')
@login_required
def pending_reminders():
    """Returns renewal reminders due in 2 days for EmailJS to send."""
    from models import Subscription
    today = date.today()
    reminder_date = today + timedelta(days=2)

    subs = Subscription.query.filter(
        Subscription.user_id == current_user.id,
        Subscription.renewal_date == reminder_date,
        Subscription.is_active == True,
        Subscription.reminder_sent == False
    ).all()

    reminders = []
    for sub in subs:
        reminders.append({
            'id': sub.id,
            'to_name': current_user.name,
            'to_email': current_user.email,
            'sub_name': sub.name,
            'sub_amount': f'₹{sub.amount:,.0f}',
            'renewal_date': sub.renewal_date.strftime('%d %b %Y')
        })

    return jsonify({'reminders': reminders})


@reports.route('/reminders/mark-sent/<int:id>', methods=['POST'])
@login_required
def mark_reminder_sent(id):
    from models import Subscription
    sub = Subscription.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    sub.reminder_sent = True
    db.session.commit()
    return jsonify({'success': True})


@reports.route('/emailjs-setup')
@login_required
def emailjs_setup():
    return render_template('emailjs_setup.html')
