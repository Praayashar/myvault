from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from flask_login import login_required, current_user
from models import db, Expense, Income, Subscription, EMI, Investment, SavingsGoal, FamilyNotice, ImportantDate, User
from datetime import datetime, date, timedelta
from sqlalchemy import func

main = Blueprint('main', __name__)

EXPENSE_CATEGORIES = ['Food', 'Travel', 'Shopping', 'Bills', 'Entertainment', 'Health', 'Fuel', 'Education', 'Groceries', 'Other']
PAYMENT_METHODS = ['UPI', 'Cash', 'Credit Card', 'Debit Card', 'Net Banking', 'Cheque']

@main.route('/dashboard')
@login_required
def dashboard():
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)

    # Weekly spending
    weekly_expenses = db.session.query(func.sum(Expense.amount)).filter(
        Expense.user_id == current_user.id,
        Expense.date >= week_start
    ).scalar() or 0

    # Monthly spending
    monthly_expenses = db.session.query(func.sum(Expense.amount)).filter(
        Expense.user_id == current_user.id,
        Expense.date >= month_start
    ).scalar() or 0

    # Monthly income
    monthly_income = db.session.query(func.sum(Income.amount)).filter(
        Income.user_id == current_user.id,
        Income.date >= month_start
    ).scalar() or 0

    # Net worth = investments + savings goals current - EMI remaining
    total_investments = db.session.query(func.sum(Investment.principal)).filter(
        Investment.user_id == current_user.id,
        Investment.is_active == True
    ).scalar() or 0

    total_savings = db.session.query(func.sum(SavingsGoal.current_amount)).filter(
        SavingsGoal.user_id == current_user.id
    ).scalar() or 0

    net_worth = total_investments + total_savings

    # Upcoming renewals (next 7 days)
    upcoming_subs = Subscription.query.filter(
        Subscription.user_id == current_user.id,
        Subscription.renewal_date >= today,
        Subscription.renewal_date <= today + timedelta(days=7),
        Subscription.is_active == True
    ).order_by(Subscription.renewal_date).all()

    # Recent expenses
    recent_expenses = Expense.query.filter_by(user_id=current_user.id)\
        .order_by(Expense.date.desc(), Expense.created_at.desc()).limit(5).all()

    # Pinned notices
    pinned_notices = FamilyNotice.query.filter_by(is_pinned=True)\
        .order_by(FamilyNotice.created_at.desc()).limit(3).all()

    # Upcoming important dates
    upcoming_dates = ImportantDate.query.filter(
        ImportantDate.user_id == current_user.id,
        ImportantDate.date >= today,
        ImportantDate.date <= today + timedelta(days=30)
    ).order_by(ImportantDate.date).limit(3).all()

    # Category breakdown this month
    category_data = db.session.query(
        Expense.category, func.sum(Expense.amount)
    ).filter(
        Expense.user_id == current_user.id,
        Expense.date >= month_start
    ).group_by(Expense.category).all()

    return render_template('dashboard.html',
        weekly_expenses=weekly_expenses,
        monthly_expenses=monthly_expenses,
        monthly_income=monthly_income,
        net_worth=net_worth,
        upcoming_subs=upcoming_subs,
        recent_expenses=recent_expenses,
        pinned_notices=pinned_notices,
        upcoming_dates=upcoming_dates,
        category_data=category_data,
        today=today,
        categories=EXPENSE_CATEGORIES,
        payment_methods=PAYMENT_METHODS
    )

@main.route('/quick-add', methods=['POST'])
@login_required
def quick_add():
    data = request.get_json()
    try:
        expense = Expense(
            user_id=current_user.id,
            amount=float(data['amount']),
            category=data['category'],
            payment_method=data.get('payment_method', 'UPI'),
            description=data.get('description', ''),
            notes=data.get('notes', ''),
            date=datetime.strptime(data.get('date', date.today().isoformat()), '%Y-%m-%d').date()
        )
        db.session.add(expense)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Expense added!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@main.route('/settings')
@login_required
def settings():
    all_users = User.query.all() if current_user.role == 'admin' else []
    return render_template('settings.html', all_users=all_users)

@main.route('/settings/simple-mode', methods=['POST'])
@login_required
def toggle_simple_mode():
    current_user.simple_mode = not current_user.simple_mode
    db.session.commit()
    return jsonify({'success': True, 'simple_mode': current_user.simple_mode})


@main.route('/quick-entry')
@login_required
def quick_entry():
    from routes.life import FuelLog, HomeTask, GasLog
    today = date.today()
    vehicles = __import__('models', fromlist=['Vehicle']).Vehicle.query.filter_by(user_id=current_user.id).all()
    return render_template('quick_entry.html',
        today=today,
        categories=EXPENSE_CATEGORIES,
        payment_methods=PAYMENT_METHODS,
        vehicles=vehicles
    )
