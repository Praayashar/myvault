from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
import logging
import requests
from models import db, Expense, Income, Subscription, Investment, EMI, SavingsGoal, BudgetLimit
from datetime import datetime, date, timedelta
from sqlalchemy import func

logger = logging.getLogger(__name__)
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
{chr(10).join(f"- {g.name}: ₹{g.current_amount:,.0f} saved of ₹{g.target_amount:,.0f}" + (f" ({g.current_amount/g.target_amount*100:.0f}%)" if g.target_amount else "") for g in goals) if goals else "- No savings goals set"}

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
    """Server-side Gemini call.

    The previous version returned the system prompt - containing the user's
    full financial snapshot - to the browser and had the browser call the AI
    provider directly, with no API key. That could never work, and it leaked
    the snapshot. Everything now stays on the server.
    """
    data = request.get_json(silent=True) or {}
    user_message = (data.get('message') or '').strip()
    history = data.get('history', [])

    if not user_message:
        return jsonify({'success': False, 'message': 'Please type a question.'}), 400

    api_key = current_app.config.get('GEMINI_API_KEY', '')
    if not api_key:
        return jsonify({
            'success': False,
            'message': 'The AI assistant is not set up yet. Add GEMINI_API_KEY in Render > Environment.'
        }), 503

    model = current_app.config.get('GEMINI_MODEL', 'gemini-2.5-flash')
    system_prompt = get_user_financial_context(current_user.id)

    # Gemini format: roles are 'user' and 'model' (not 'assistant').
    contents = []
    for msg in history[-10:]:
        role = 'model' if msg.get('role') in ('assistant', 'model') else 'user'
        text = (msg.get('content') or '').strip()
        if text:
            contents.append({'role': role, 'parts': [{'text': text}]})
    contents.append({'role': 'user', 'parts': [{'text': user_message}]})

    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{model}:generateContent")

    try:
        resp = requests.post(
            url,
            headers={
                'Content-Type': 'application/json',
                'x-goog-api-key': api_key,
            },
            json={
                'systemInstruction': {'parts': [{'text': system_prompt}]},
                'contents': contents,
                'generationConfig': {
                    'maxOutputTokens': 1000,
                    'temperature': 0.7,
                },
            },
            timeout=45,
        )
    except requests.Timeout:
        return jsonify({'success': False,
                        'message': 'The assistant took too long to reply. Please try again.'}), 504
    except requests.RequestException as e:
        logger.error("Gemini request failed: %s", e)
        return jsonify({'success': False,
                        'message': 'Could not reach the assistant. Check your internet and try again.'}), 502

    if resp.status_code != 200:
        logger.error("Gemini returned %s: %s", resp.status_code, resp.text[:500])
        msg = 'The assistant could not answer right now.'
        if resp.status_code in (401, 403):
            msg = 'The AI key was rejected. Check GEMINI_API_KEY in Render.'
        elif resp.status_code == 429:
            msg = 'Too many questions just now. Please wait a minute and try again.'
        return jsonify({'success': False, 'message': msg}), 502

    try:
        payload = resp.json()
        reply = payload['candidates'][0]['content']['parts'][0]['text']
    except (KeyError, IndexError, ValueError):
        # Most often a safety block or an empty candidate.
        logger.error("Unexpected Gemini response: %s", resp.text[:500])
        return jsonify({'success': False,
                        'message': 'The assistant did not return an answer. Please rephrase and try again.'}), 502

    return jsonify({'success': True, 'reply': reply})
