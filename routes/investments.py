from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from models import db, Investment, SavingsGoal
from datetime import datetime, date
from sqlalchemy import func

investments = Blueprint('investments', __name__)

@investments.route('/investments')
@login_required
def index():
    today = date.today()
    all_inv = Investment.query.filter_by(user_id=current_user.id).order_by(Investment.maturity_date).all()

    fds = [i for i in all_inv if i.type == 'FD']
    rds = [i for i in all_inv if i.type == 'RD']
    mfs = [i for i in all_inv if i.type == 'MF']

    total_invested = sum(i.principal for i in all_inv if i.is_active)
    total_maturity = sum(i.maturity_amount or i.principal for i in all_inv if i.is_active)

    goals = SavingsGoal.query.filter_by(user_id=current_user.id).order_by(SavingsGoal.target_date).all()
    total_goal_target = sum(g.target_amount for g in goals)
    total_goal_saved = sum(g.current_amount for g in goals)

    # Maturing soon (next 30 days)
    maturing_soon = [i for i in all_inv if i.is_active and i.maturity_date and
                     0 <= (i.maturity_date - today).days <= 30]

    return render_template('investments.html',
        today=today, fds=fds, rds=rds, mfs=mfs,
        total_invested=total_invested,
        total_maturity=total_maturity,
        expected_returns=total_maturity - total_invested,
        goals=goals,
        total_goal_target=total_goal_target,
        total_goal_saved=total_goal_saved,
        maturing_soon=maturing_soon
    )

@investments.route('/investments/add', methods=['POST'])
@login_required
def add_investment():
    data = request.get_json()
    try:
        inv = Investment(
            user_id=current_user.id,
            type=data['type'],
            name=data['name'],
            principal=float(data['principal']),
            interest_rate=float(data.get('interest_rate') or 0),
            start_date=datetime.strptime(data['start_date'], '%Y-%m-%d').date() if data.get('start_date') else date.today(),
            maturity_date=datetime.strptime(data['maturity_date'], '%Y-%m-%d').date() if data.get('maturity_date') else None,
            maturity_amount=float(data.get('maturity_amount') or 0) or None,
            bank_name=data.get('bank_name', ''),
            notes=data.get('notes', '')
        )
        # Auto-calculate maturity amount if not provided
        if not inv.maturity_amount and inv.interest_rate and inv.maturity_date:
            years = (inv.maturity_date - inv.start_date).days / 365
            if data['type'] in ('FD', 'RD'):
                inv.maturity_amount = round(inv.principal * ((1 + inv.interest_rate/100) ** years), 2)
        db.session.add(inv)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@investments.route('/investments/close/<int:id>', methods=['POST'])
@login_required
def close_investment(id):
    inv = Investment.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    inv.is_active = False
    db.session.commit()
    return jsonify({'success': True})

@investments.route('/investments/delete/<int:id>', methods=['POST'])
@login_required
def delete_investment(id):
    inv = Investment.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(inv)
    db.session.commit()
    return jsonify({'success': True})

# ===== SAVINGS GOALS =====
@investments.route('/goals/add', methods=['POST'])
@login_required
def add_goal():
    data = request.get_json()
    try:
        goal = SavingsGoal(
            user_id=current_user.id,
            name=data['name'],
            target_amount=float(data['target_amount']),
            current_amount=float(data.get('current_amount', 0)),
            target_date=datetime.strptime(data['target_date'], '%Y-%m-%d').date() if data.get('target_date') else None
        )
        db.session.add(goal)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@investments.route('/goals/update/<int:id>', methods=['POST'])
@login_required
def update_goal(id):
    goal = SavingsGoal.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    data = request.get_json()
    goal.current_amount = float(data.get('current_amount', goal.current_amount))
    db.session.commit()
    return jsonify({'success': True})

@investments.route('/goals/delete/<int:id>', methods=['POST'])
@login_required
def delete_goal(id):
    goal = SavingsGoal.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(goal)
    db.session.commit()
    return jsonify({'success': True})
