from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from models import db, PasswordVault, AccountDirectory, DocumentVault
from datetime import datetime, date
import base64

vault = Blueprint('vault', __name__)

# Simple reversible encoding (not encryption - personal use only)
def encode_password(pwd):
    return base64.b64encode(pwd.encode()).decode()

def decode_password(encoded):
    try:
        return base64.b64decode(encoded.encode()).decode()
    except:
        return encoded

# ===== PASSWORD VAULT =====
@vault.route('/vault/passwords')
@login_required
def passwords():
    items = PasswordVault.query.filter_by(user_id=current_user.id).order_by(PasswordVault.category, PasswordVault.app_name).all()
    categories = sorted(set(i.category for i in items))
    return render_template('vault_passwords.html', items=items, categories=categories, decode_password=decode_password)

@vault.route('/vault/passwords/add', methods=['POST'])
@login_required
def add_password():
    data = request.get_json()
    try:
        item = PasswordVault(
            user_id=current_user.id,
            app_name=data['app_name'],
            category=data.get('category', 'Other'),
            username=data.get('username', ''),
            email=data.get('email', ''),
            password=encode_password(data['password']),
            website_url=data.get('website_url', ''),
            notes=data.get('notes', '')
        )
        db.session.add(item)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@vault.route('/vault/passwords/get/<int:id>')
@login_required
def get_password(id):
    item = PasswordVault.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    return jsonify({
        'app_name': item.app_name,
        'username': item.username,
        'email': item.email,
        'password': decode_password(item.password),
        'website_url': item.website_url,
        'notes': item.notes
    })

@vault.route('/vault/passwords/delete/<int:id>', methods=['POST'])
@login_required
def delete_password(id):
    item = PasswordVault.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    return jsonify({'success': True})

# ===== ACCOUNT DIRECTORY =====
@vault.route('/vault/accounts')
@login_required
def accounts():
    items = AccountDirectory.query.filter_by(user_id=current_user.id).order_by(AccountDirectory.account_type, AccountDirectory.account_name).all()
    return render_template('vault_accounts.html', items=items)

@vault.route('/vault/accounts/add', methods=['POST'])
@login_required
def add_account():
    data = request.get_json()
    try:
        item = AccountDirectory(
            user_id=current_user.id,
            account_type=data.get('account_type', 'Bank'),
            account_name=data['account_name'],
            account_number=data.get('account_number', ''),
            ifsc_code=data.get('ifsc_code', ''),
            branch=data.get('branch', ''),
            notes=data.get('notes', '')
        )
        db.session.add(item)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@vault.route('/vault/accounts/delete/<int:id>', methods=['POST'])
@login_required
def delete_account(id):
    item = AccountDirectory.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    return jsonify({'success': True})

# ===== DOCUMENT VAULT =====
@vault.route('/vault/documents')
@login_required
def documents():
    today = date.today()
    items = DocumentVault.query.filter_by(user_id=current_user.id).order_by(DocumentVault.doc_type, DocumentVault.doc_name).all()
    expiring_soon = [i for i in items if i.expiry_date and 0 <= (i.expiry_date - today).days <= 90]
    return render_template('vault_documents.html', items=items, today=today, expiring_soon=expiring_soon)

@vault.route('/vault/documents/add', methods=['POST'])
@login_required
def add_document():
    data = request.get_json()
    try:
        item = DocumentVault(
            user_id=current_user.id,
            doc_type=data.get('doc_type', 'Other'),
            doc_name=data['doc_name'],
            doc_number=data.get('doc_number', ''),
            expiry_date=datetime.strptime(data['expiry_date'], '%Y-%m-%d').date() if data.get('expiry_date') else None,
            notes=data.get('notes', '')
        )
        db.session.add(item)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@vault.route('/vault/documents/delete/<int:id>', methods=['POST'])
@login_required
def delete_document(id):
    item = DocumentVault.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    return jsonify({'success': True})

# ===== TICKET VAULT =====
@vault.route('/vault/tickets')
@login_required
def tickets():
    today = date.today()
    items = TicketVault.query.filter_by(user_id=current_user.id).order_by(TicketVault.travel_date.desc()).all()
    return render_template('vault_tickets.html', items=items, today=today)

@vault.route('/vault/tickets/add', methods=['POST'])
@login_required
def add_ticket():
    data = request.get_json()
    try:
        item = TicketVault(
            user_id=current_user.id,
            title=data['title'],
            ticket_type=data.get('ticket_type', 'Train'),
            booking_ref=data.get('booking_ref', ''),
            from_location=data.get('from_location', ''),
            to_location=data.get('to_location', ''),
            travel_date=datetime.strptime(data['travel_date'], '%Y-%m-%d').date() if data.get('travel_date') else None,
            amount=float(data.get('amount') or 0),
            notes=data.get('notes', '')
        )
        db.session.add(item)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@vault.route('/vault/tickets/delete/<int:id>', methods=['POST'])
@login_required
def delete_ticket(id):
    item = TicketVault.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    return jsonify({'success': True})

# ===== TICKET MODEL =====
class TicketVault(db.Model):
    __tablename__ = 'ticket_vault'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    ticket_type = db.Column(db.String(30), default='Train')
    booking_ref = db.Column(db.String(100))
    from_location = db.Column(db.String(100))
    to_location = db.Column(db.String(100))
    travel_date = db.Column(db.Date)
    amount = db.Column(db.Float, default=0)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
