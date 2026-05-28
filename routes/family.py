from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from models import db, User, FamilyNotice, ImportantDate, Expense, Income, Subscription, Investment, SavingsGoal
from datetime import datetime, date, timedelta
from sqlalchemy import func

family = Blueprint('family', __name__)

@family.route('/family')
@login_required
def index():
    today = date.today()
    month_start = today.replace(day=1)
    all_users = User.query.all()

    # Build per-user summary
    summaries = []
    for u in all_users:
        monthly_exp = db.session.query(func.sum(Expense.amount)).filter(
            Expense.user_id == u.id, Expense.date >= month_start
        ).scalar() or 0
        monthly_inc = db.session.query(func.sum(Income.amount)).filter(
            Income.user_id == u.id, Income.date >= month_start
        ).scalar() or 0
        total_inv = db.session.query(func.sum(Investment.principal)).filter(
            Investment.user_id == u.id, Investment.is_active == True
        ).scalar() or 0
        summaries.append({
            'user': u,
            'monthly_exp': monthly_exp,
            'monthly_inc': monthly_inc,
            'balance': monthly_inc - monthly_exp,
            'net_worth': total_inv
        })

    # Combined family totals
    total_exp = sum(s['monthly_exp'] for s in summaries)
    total_inc = sum(s['monthly_inc'] for s in summaries)
    total_nw = sum(s['net_worth'] for s in summaries)

    # Upcoming renewals for whole family
    family_subs = Subscription.query.filter(
        Subscription.renewal_date >= today,
        Subscription.renewal_date <= today + timedelta(days=7),
        Subscription.is_active == True
    ).order_by(Subscription.renewal_date).all()

    # Notices
    notices = FamilyNotice.query.order_by(FamilyNotice.is_pinned.desc(), FamilyNotice.created_at.desc()).limit(10).all()

    # Upcoming important dates (all users, next 30 days)
    upcoming_dates = ImportantDate.query.filter(
        ImportantDate.date >= today,
        ImportantDate.date <= today + timedelta(days=30)
    ).order_by(ImportantDate.date).all()

    return render_template('family.html',
        summaries=summaries,
        total_exp=total_exp,
        total_inc=total_inc,
        total_nw=total_nw,
        family_subs=family_subs,
        notices=notices,
        upcoming_dates=upcoming_dates,
        today=today
    )

# ===== NOTICES =====
@family.route('/family/notice/add', methods=['POST'])
@login_required
def add_notice():
    data = request.get_json()
    try:
        notice = FamilyNotice(
            user_id=current_user.id,
            message=data['message'],
            is_pinned=data.get('is_pinned', False)
        )
        db.session.add(notice)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@family.route('/family/notice/pin/<int:id>', methods=['POST'])
@login_required
def pin_notice(id):
    notice = FamilyNotice.query.get_or_404(id)
    notice.is_pinned = not notice.is_pinned
    db.session.commit()
    return jsonify({'success': True, 'is_pinned': notice.is_pinned})

@family.route('/family/notice/delete/<int:id>', methods=['POST'])
@login_required
def delete_notice(id):
    notice = FamilyNotice.query.get_or_404(id)
    db.session.delete(notice)
    db.session.commit()
    return jsonify({'success': True})

# ===== IMPORTANT DATES =====
@family.route('/family/dates/add', methods=['POST'])
@login_required
def add_date():
    data = request.get_json()
    try:
        d = ImportantDate(
            user_id=current_user.id,
            title=data['title'],
            date=datetime.strptime(data['date'], '%Y-%m-%d').date(),
            type=data.get('type', 'Birthday'),
            reminder_days=int(data.get('reminder_days', 3)),
            notes=data.get('notes', '')
        )
        db.session.add(d)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@family.route('/family/dates/delete/<int:id>', methods=['POST'])
@login_required
def delete_date(id):
    d = ImportantDate.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(d)
    db.session.commit()
    return jsonify({'success': True})
