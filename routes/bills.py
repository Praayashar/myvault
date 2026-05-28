from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from models import db, Subscription, EMI, Insurance
from datetime import datetime, date, timedelta

bills = Blueprint('bills', __name__)

# ===== SUBSCRIPTIONS =====
@bills.route('/subscriptions')
@login_required
def subscriptions():
    today = date.today()
    subs = Subscription.query.filter_by(user_id=current_user.id).order_by(Subscription.renewal_date).all()
    total_monthly = sum(
        s.amount if s.billing_cycle == 'monthly' else
        s.amount / 12 if s.billing_cycle == 'yearly' else
        s.amount / 3
        for s in subs if s.is_active
    )
    return render_template('subscriptions.html', subs=subs, today=today, total_monthly=round(total_monthly, 2))

@bills.route('/subscriptions/add', methods=['POST'])
@login_required
def add_subscription():
    data = request.get_json()
    try:
        sub = Subscription(
            user_id=current_user.id,
            name=data['name'],
            amount=float(data['amount']),
            billing_cycle=data.get('billing_cycle', 'monthly'),
            renewal_date=datetime.strptime(data['renewal_date'], '%Y-%m-%d').date(),
            category=data.get('category', 'Entertainment'),
            notes=data.get('notes', '')
        )
        db.session.add(sub)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@bills.route('/subscriptions/toggle/<int:id>', methods=['POST'])
@login_required
def toggle_subscription(id):
    sub = Subscription.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    sub.is_active = not sub.is_active
    db.session.commit()
    return jsonify({'success': True, 'is_active': sub.is_active})

@bills.route('/subscriptions/delete/<int:id>', methods=['POST'])
@login_required
def delete_subscription(id):
    sub = Subscription.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(sub)
    db.session.commit()
    return jsonify({'success': True})

@bills.route('/subscriptions/renew/<int:id>', methods=['POST'])
@login_required
def renew_subscription(id):
    sub = Subscription.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    if sub.billing_cycle == 'monthly':
        sub.renewal_date = sub.renewal_date.replace(month=sub.renewal_date.month % 12 + 1) if sub.renewal_date.month < 12 else sub.renewal_date.replace(year=sub.renewal_date.year + 1, month=1)
    elif sub.billing_cycle == 'yearly':
        sub.renewal_date = sub.renewal_date.replace(year=sub.renewal_date.year + 1)
    elif sub.billing_cycle == 'quarterly':
        sub.renewal_date = sub.renewal_date + timedelta(days=90)
    sub.reminder_sent = False
    db.session.commit()
    return jsonify({'success': True})

# ===== EMI =====
@bills.route('/emi')
@login_required
def emi_list():
    emis = EMI.query.filter_by(user_id=current_user.id).order_by(EMI.created_at.desc()).all()
    total_emi = sum(e.emi_amount for e in emis if e.paid_installments < e.total_installments)
    return render_template('emi.html', emis=emis, total_emi=total_emi)

@bills.route('/emi/add', methods=['POST'])
@login_required
def add_emi():
    data = request.get_json()
    try:
        emi = EMI(
            user_id=current_user.id,
            name=data['name'],
            total_amount=float(data['total_amount']),
            emi_amount=float(data['emi_amount']),
            total_installments=int(data['total_installments']),
            paid_installments=int(data.get('paid_installments', 0)),
            due_date=int(data.get('due_date', 1)),
            start_date=datetime.strptime(data['start_date'], '%Y-%m-%d').date() if data.get('start_date') else date.today(),
            notes=data.get('notes', '')
        )
        db.session.add(emi)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@bills.route('/emi/pay/<int:id>', methods=['POST'])
@login_required
def pay_emi(id):
    emi = EMI.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    if emi.paid_installments < emi.total_installments:
        emi.paid_installments += 1
        db.session.commit()
    return jsonify({'success': True, 'paid': emi.paid_installments, 'total': emi.total_installments})

@bills.route('/emi/delete/<int:id>', methods=['POST'])
@login_required
def delete_emi(id):
    emi = EMI.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(emi)
    db.session.commit()
    return jsonify({'success': True})

# ===== INSURANCE =====
@bills.route('/insurance')
@login_required
def insurance_list():
    today = date.today()
    policies = Insurance.query.filter_by(user_id=current_user.id).order_by(Insurance.premium_due_date).all()
    return render_template('insurance.html', policies=policies, today=today)

@bills.route('/insurance/add', methods=['POST'])
@login_required
def add_insurance():
    data = request.get_json()
    try:
        ins = Insurance(
            user_id=current_user.id,
            type=data['type'],
            provider=data['provider'],
            policy_number=data.get('policy_number', ''),
            premium_amount=float(data.get('premium_amount', 0)),
            premium_due_date=datetime.strptime(data['premium_due_date'], '%Y-%m-%d').date() if data.get('premium_due_date') else None,
            sum_insured=float(data.get('sum_insured', 0)),
            nominee=data.get('nominee', ''),
            notes=data.get('notes', '')
        )
        db.session.add(ins)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@bills.route('/insurance/delete/<int:id>', methods=['POST'])
@login_required
def delete_insurance(id):
    ins = Insurance.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(ins)
    db.session.commit()
    return jsonify({'success': True})
