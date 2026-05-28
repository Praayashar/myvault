from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from models import db, Expense, Income, Subscription, Investment, EMI, SavingsGoal, BudgetLimit
from datetime import datetime, date, timedelta
from sqlalchemy import func

ai = Blueprint('ai', __name__)

def get_user_financial_context(user_id):
    """Build a financial summary for the AI to use as context."""
    today = date.today()
    month_start = today.replace(day=1)
    week_start = today - timedelta(days=today.weekday())

    monthly_exp = db.session.query(func.sum(Expense.amount)).filter(
        Expense.user_id == user_id, Expense.date >= month_start
    ).scalar() or 0

    monthly_inc = db.session.query(func.sum(Income.amount)).filter(
        Income.user_id == user_id, Income.date >= month_start
    ).scalar() or 0

    weekly_exp = db.session.query(func.sum(Expense.amount)).filter(
        Expense.user_id == user_id, Expense.date >= week_start
    ).scalar() or 0

    category_data = db.session.query(
        Expense.category, func.sum(Expense.amount)
    ).filter(
        Expense.user_id == user_id, Expense.date >= month_start
    ).group_by(Expense.category).order_by(func.sum(Expense.amount).desc()).all()

    total_investments = db.session.query(func.sum(Investment.principal)).filter(
        Investment.user_id == user_id, Investment.is_active == True
    ).scalar() or 0

    active_emis = EMI.query.filter_by(user_id=user_id).filter(
        EMI.paid_installments < EMI.total_installments
    ).all()
    total_emi = sum(e.emi_amount for e in active_emis)

    active_subs = Subscription.query.filter_by(user_id=user_id, is_active=True).all()
    total_subs = sum(
        s.amount if s.billing_cycle == 'monthly' else
        s.amount / 12 if s.billing_cycle == 'yearly' else s.amount / 3
        for s in active_subs
    )

    goals = SavingsGoal.query.filter_by(user_id=user_id).all()

    budgets = BudgetLimit.query.filter_by(user_id=user_id).all()
    budget_alerts = []
    for b in budgets:
        spent = db.session.query(func.sum(Expense.amount)).filter(
            Expense.user_id == user_id,
            Expense.category == b.category,
            Expense.date >= month_start
        ).scalar() or 0
        pct = (spent / b.monthly_limit * 100) if b.monthly_limit else 0
        if pct >= 70:
            budget_alerts.append(f"{b.category}: {pct:.0f}% of ₹{b.monthly_limit:,.0f} budget used")

    upcoming_renewals = Subscription.query.filter(
        Subscription.user_id == user_id,
        Subscription.renewal_date >= today,
        Subscription.renewal_date <= today + timedelta(days=7),
        Subscription.is_active == True
    ).all()

    context = f"""You are MyVault AI, a personal financial assistant for an Indian household. 
Today's date: {today.strftime('%d %B %Y')}

USER'S FINANCIAL SNAPSHOT:
- Monthly Income: ₹{monthly_inc:,.0f}
- Monthly Expenses: ₹{monthly_exp:,.0f}
- Weekly Expenses: ₹{weekly_exp:,.0f}
- Monthly Balance: ₹{monthly_inc - monthly_exp:,.0f} ({'savings' if monthly_inc >= monthly_exp else 'deficit'})
- Total Investments (FD/RD/MF): ₹{total_investments:,.0f}
- Monthly EMI burden: ₹{total_emi:,.0f}
- Monthly subscription cost: ₹{total_subs:,.0f}

SPENDING BY CATEGORY THIS MONTH:
{chr(10).join(f"- {cat}: ₹{amt:,.0f}" for cat, amt in category_data) if category_data else "- No expenses logged yet"}

SAVINGS GOALS:
{chr(10).join(f"- {g.name}: ₹{g.current_amount:,.0f} saved of ₹{g.target_amount:,.0f} ({g.current_amount/g.target_amount*100:.0f}%)" for g in goals) if goals else "- No savings goals set"}

BUDGET ALERTS:
{chr(10).join(f"- {a}" for a in budget_alerts) if budget_alerts else "- All budgets within limits"}

UPCOMING RENEWALS (next 7 days):
{chr(10).join(f"- {s.name}: ₹{s.amount:,.0f} on {s.renewal_date.strftime('%d %b')}" for s in upcoming_renewals) if upcoming_renewals else "- No renewals in next 7 days"}

INSTRUCTIONS:
- Respond in a friendly, personal tone like a trusted financial advisor
- Use Indian Rupee (₹) for all amounts
- Keep responses concise and actionable
- Give specific advice based on the user's actual data above
- If asked something outside finance, gently redirect to financial topics
- Use simple language since this app is used by family including elderly members
"""
    return context


@ai.route('/ai')
@login_required
def index():
    return render_template('ai.html')


@ai.route('/ai/chat', methods=['POST'])
@login_required
def chat():
    data = request.get_json()
    user_message = data.get('message', '').strip()
    conversation_history = data.get('history', [])

    if not user_message:
        return jsonify({'success': False, 'message': 'Empty message'}), 400

    context = get_user_financial_context(current_user.id)

    # Build messages for Claude API
    messages = []
    for msg in conversation_history[-10:]:  # last 10 messages for context
        messages.append({'role': msg['role'], 'content': msg['content']})
    messages.append({'role': 'user', 'content': user_message})

    return jsonify({
        'success': True,
        'system_prompt': context,
        'messages': messages
    })
