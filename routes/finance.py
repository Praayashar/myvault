from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Expense, Income, BudgetLimit
from datetime import datetime, date, timedelta
from sqlalchemy import func
import calendar

finance = Blueprint('finance', __name__)

CATEGORIES = ['Food', 'Travel', 'Shopping', 'Bills', 'Entertainment', 'Health', 'Fuel', 'Education', 'Groceries', 'Other']
PAYMENT_METHODS = ['UPI', 'Cash', 'Credit Card', 'Debit Card', 'Net Banking', 'Cheque']

@finance.route('/finance')
@login_required
def index():
    today = date.today()
    month_start = today.replace(day=1)
    week_start = today - timedelta(days=today.weekday())

    # Monthly summary
    monthly_exp = db.session.query(func.sum(Expense.amount)).filter(
        Expense.user_id == current_user.id,
        Expense.date >= month_start
    ).scalar() or 0

    monthly_inc = db.session.query(func.sum(Income.amount)).filter(
        Income.user_id == current_user.id,
        Income.date >= month_start
    ).scalar() or 0

    # Weekly expenses
    weekly_exp = db.session.query(func.sum(Expense.amount)).filter(
        Expense.user_id == current_user.id,
        Expense.date >= week_start
    ).scalar() or 0

    # Category breakdown
    category_data = db.session.query(
        Expense.category, func.sum(Expense.amount)
    ).filter(
        Expense.user_id == current_user.id,
        Expense.date >= month_start
    ).group_by(Expense.category).order_by(func.sum(Expense.amount).desc()).all()

    # Payment method breakdown
    payment_data = db.session.query(
        Expense.payment_method, func.sum(Expense.amount)
    ).filter(
        Expense.user_id == current_user.id,
        Expense.date >= month_start
    ).group_by(Expense.payment_method).all()

    # Budget limits
    budgets = BudgetLimit.query.filter_by(user_id=current_user.id).all()
    budget_status = []
    for b in budgets:
        spent = db.session.query(func.sum(Expense.amount)).filter(
            Expense.user_id == current_user.id,
            Expense.category == b.category,
            Expense.date >= month_start
        ).scalar() or 0
        pct = min((spent / b.monthly_limit * 100), 100) if b.monthly_limit > 0 else 0
        budget_status.append({
            'category': b.category,
            'limit': b.monthly_limit,
            'spent': spent,
            'remaining': max(b.monthly_limit - spent, 0),
            'pct': round(pct),
            'id': b.id
        })

    # Last 30 expenses
    expenses = Expense.query.filter_by(user_id=current_user.id)\
        .order_by(Expense.date.desc(), Expense.created_at.desc()).limit(30).all()

    # Weekly chart data (last 7 days)
    chart_labels = []
    chart_data = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        amt = db.session.query(func.sum(Expense.amount)).filter(
            Expense.user_id == current_user.id,
            Expense.date == d
        ).scalar() or 0
        chart_labels.append(d.strftime('%a'))
        chart_data.append(round(amt, 2))

    # Monthly chart (last 6 months)
    month_labels = []
    month_data_exp = []
    month_data_inc = []
    for i in range(5, -1, -1):
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12
            y -= 1
        ms = date(y, m, 1)
        me = date(y, m, calendar.monthrange(y, m)[1])
        exp = db.session.query(func.sum(Expense.amount)).filter(
            Expense.user_id == current_user.id,
            Expense.date >= ms, Expense.date <= me
        ).scalar() or 0
        inc = db.session.query(func.sum(Income.amount)).filter(
            Income.user_id == current_user.id,
            Income.date >= ms, Income.date <= me
        ).scalar() or 0
        month_labels.append(ms.strftime('%b'))
        month_data_exp.append(round(exp, 2))
        month_data_inc.append(round(inc, 2))

    return render_template('finance.html',
        today=today,
        monthly_exp=monthly_exp,
        monthly_inc=monthly_inc,
        weekly_exp=weekly_exp,
        balance=monthly_inc - monthly_exp,
        category_data=category_data,
        payment_data=payment_data,
        budget_status=budget_status,
        expenses=expenses,
        categories=CATEGORIES,
        payment_methods=PAYMENT_METHODS,
        chart_labels=chart_labels,
        chart_data=chart_data,
        month_labels=month_labels,
        month_data_exp=month_data_exp,
        month_data_inc=month_data_inc
    )

@finance.route('/finance/expense/add', methods=['POST'])
@login_required
def add_expense():
    data = request.get_json()
    try:
        exp = Expense(
            user_id=current_user.id,
            amount=float(data['amount']),
            category=data['category'],
            payment_method=data.get('payment_method', 'UPI'),
            description=data.get('description', ''),
            notes=data.get('notes', ''),
            date=datetime.strptime(data.get('date', date.today().isoformat()), '%Y-%m-%d').date(),
            is_recurring=data.get('is_recurring', False)
        )
        db.session.add(exp)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@finance.route('/finance/expense/delete/<int:id>', methods=['POST'])
@login_required
def delete_expense(id):
    exp = Expense.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(exp)
    db.session.commit()
    return jsonify({'success': True})

@finance.route('/finance/income/add', methods=['POST'])
@login_required
def add_income():
    data = request.get_json()
    try:
        inc = Income(
            user_id=current_user.id,
            amount=float(data['amount']),
            source=data['source'],
            description=data.get('description', ''),
            date=datetime.strptime(data.get('date', date.today().isoformat()), '%Y-%m-%d').date(),
            is_recurring=data.get('is_recurring', False)
        )
        db.session.add(inc)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@finance.route('/finance/income/delete/<int:id>', methods=['POST'])
@login_required
def delete_income(id):
    inc = Income.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(inc)
    db.session.commit()
    return jsonify({'success': True})

@finance.route('/finance/income/list')
@login_required
def income_list():
    incomes = Income.query.filter_by(user_id=current_user.id)\
        .order_by(Income.date.desc()).limit(30).all()
    return jsonify([{
        'id': i.id, 'amount': i.amount, 'source': i.source,
        'description': i.description, 'date': i.date.isoformat()
    } for i in incomes])

@finance.route('/finance/budget/add', methods=['POST'])
@login_required
def add_budget():
    data = request.get_json()
    existing = BudgetLimit.query.filter_by(
        user_id=current_user.id, category=data['category']
    ).first()
    if existing:
        existing.monthly_limit = float(data['limit'])
    else:
        b = BudgetLimit(user_id=current_user.id, category=data['category'], monthly_limit=float(data['limit']))
        db.session.add(b)
    db.session.commit()
    return jsonify({'success': True})

@finance.route('/finance/budget/delete/<int:id>', methods=['POST'])
@login_required
def delete_budget(id):
    b = BudgetLimit.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(b)
    db.session.commit()
    return jsonify({'success': True})

@finance.route('/finance/calendar')
@login_required
def calendar_view():
    today = date.today()
    year = int(request.args.get('year', today.year))
    month = int(request.args.get('month', today.month))
    month_start = date(year, month, 1)
    month_end = date(year, month, calendar.monthrange(year, month)[1])

    expenses = Expense.query.filter(
        Expense.user_id == current_user.id,
        Expense.date >= month_start,
        Expense.date <= month_end
    ).all()

    cal_data = {}
    for exp in expenses:
        key = exp.date.isoformat()
        cal_data[key] = cal_data.get(key, 0) + exp.amount

    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    return render_template('calendar.html',
        today=today, year=year, month=month,
        month_name=month_start.strftime('%B %Y'),
        cal_data=cal_data,
        calendar=calendar,
        month_start=month_start,
        prev_month=prev_month, prev_year=prev_year,
        next_month=next_month, next_year=next_year
    )
