from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User
from datetime import datetime, timedelta
import secrets

HASH_METHOD = 'pbkdf2:sha256'
auth = Blueprint('auth', __name__)

@auth.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user, remember=True)
            return redirect(url_for('main.dashboard'))
        flash('Invalid email or password.', 'error')
    return render_template('login.html')

@auth.route('/register', methods=['GET', 'POST'])
def register():
    user_count = User.query.count()
    if user_count >= 2 and (not current_user.is_authenticated or current_user.role != 'admin'):
        flash('Registration is closed. Contact admin.', 'error')
        return redirect(url_for('auth.login'))
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        if not name or not email or not password:
            flash('All fields are required.', 'error')
            return render_template('register.html', first_setup=(user_count == 0))
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'error')
            return render_template('register.html', first_setup=(user_count == 0))
        role = 'admin' if user_count == 0 else 'member'
        user = User(
            name=name, email=email,
            password_hash=generate_password_hash(password, method=HASH_METHOD),
            role=role
        )
        db.session.add(user)
        db.session.commit()
        if user_count == 0:
            login_user(user)
            flash(f'Welcome to MyVault, {name}!', 'success')
            return redirect(url_for('main.dashboard'))
        flash('Profile created successfully!', 'success')
        return redirect(url_for('main.dashboard'))
    return render_template('register.html', first_setup=(user_count == 0))

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

# ===== FORGOT PASSWORD =====
@auth.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        user = User.query.filter_by(email=email).first()
        if user:
            token = secrets.token_urlsafe(32)
            user.reset_token = token
            user.reset_token_expiry = datetime.utcnow() + timedelta(hours=1)
            db.session.commit()
            reset_url = url_for('auth.reset_password', token=token, _external=True)
            return render_template('forgot_password.html',
                sent=True, email=email, reset_url=reset_url,
                user_name=user.name
            )
        flash('No account found with that email.', 'error')
    return render_template('forgot_password.html', sent=False)

@auth.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = User.query.filter_by(reset_token=token).first()
    if not user or not user.reset_token_expiry or user.reset_token_expiry < datetime.utcnow():
        flash('Reset link is invalid or has expired.', 'error')
        return redirect(url_for('auth.forgot_password'))
    if request.method == 'POST':
        password = request.form.get('password', '').strip()
        confirm = request.form.get('confirm_password', '').strip()
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'error')
            return render_template('reset_password.html', token=token)
        if password != confirm:
            flash('Passwords do not match.', 'error')
            return render_template('reset_password.html', token=token)
        user.password_hash = generate_password_hash(password, method=HASH_METHOD)
        user.reset_token = None
        user.reset_token_expiry = None
        db.session.commit()
        flash('Password reset successfully! Please login.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('reset_password.html', token=token, user=user)
