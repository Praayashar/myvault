from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, LoginAttempt
from datetime import datetime, timedelta
import secrets
import logging

logger = logging.getLogger(__name__)

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
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()

        # Rate limit: stop unlimited password guessing against an account.
        locked, minutes = _is_locked_out(email)
        if locked:
            flash(f'Too many failed attempts. Please wait {minutes} minute(s) and try again.', 'error')
            return render_template('login.html')

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            _record_attempt(email, True)
            login_user(user, remember=True)
            return redirect(url_for('main.dashboard'))

        _record_attempt(email, False)
        flash('Invalid email or password.', 'error')
    return render_template('login.html')


def _is_locked_out(email):
    """Return (locked, minutes_remaining) for this email + client address."""
    cfg = current_app.config
    window_start = datetime.utcnow() - timedelta(minutes=cfg['LOGIN_LOCKOUT_MINUTES'])
    for identifier in (email, _client_ip()):
        if not identifier:
            continue
        failures = LoginAttempt.query.filter(
            LoginAttempt.identifier == identifier,
            LoginAttempt.successful == False,  # noqa: E712
            LoginAttempt.attempted_at >= window_start,
        ).count()
        if failures >= cfg['MAX_LOGIN_ATTEMPTS']:
            newest = LoginAttempt.query.filter(
                LoginAttempt.identifier == identifier,
                LoginAttempt.successful == False,  # noqa: E712
            ).order_by(LoginAttempt.attempted_at.desc()).first()
            if newest:
                unlock_at = newest.attempted_at + timedelta(minutes=cfg['LOGIN_LOCKOUT_MINUTES'])
                remaining = max(1, int((unlock_at - datetime.utcnow()).total_seconds() // 60) + 1)
                return True, remaining
    return False, 0


def _client_ip():
    fwd = request.headers.get('X-Forwarded-For', '')
    if fwd:
        return fwd.split(',')[0].strip()
    return request.remote_addr or ''


def _record_attempt(email, successful):
    try:
        db.session.add(LoginAttempt(identifier=email, successful=successful))
        ip = _client_ip()
        if ip:
            db.session.add(LoginAttempt(identifier=ip, successful=successful))
        if successful:
            # Clear the slate for this email once they get in.
            LoginAttempt.query.filter(
                LoginAttempt.identifier.in_([e for e in (email, _client_ip()) if e]),
                LoginAttempt.successful == False,  # noqa: E712
            ).delete(synchronize_session=False)
        # Housekeeping: drop rows older than a day so the table stays small.
        LoginAttempt.query.filter(
            LoginAttempt.attempted_at < datetime.utcnow() - timedelta(days=1)
        ).delete(synchronize_session=False)
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("could not record login attempt")

@auth.route('/register', methods=['GET', 'POST'])
def register():
    user_count = User.query.count()
    if user_count >= 2 and (not current_user.is_authenticated or current_user.role != 'admin'):
        flash('Registration is closed. Contact admin.', 'error')
        return redirect(url_for('auth.login'))
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        if not name or not email or not password:
            flash('All fields are required.', 'error')
            return render_template('register.html', first_setup=(user_count == 0))
        if len(password) < 8:
            flash('Password must be at least 8 characters.', 'error')
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
# The old version rendered a working reset link on screen to whoever typed an
# email address, so anyone who knew the address could take over the account.
# It now only ever shows a neutral message. The admin resets family passwords
# from Settings instead.
@auth.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        user = User.query.filter_by(email=email).first()
        if user:
            # Token is generated and stored, but shown to nobody. It exists so
            # the admin can hand over a link deliberately if ever needed.
            token = secrets.token_urlsafe(32)
            user.reset_token = token
            user.reset_token_expiry = datetime.utcnow() + timedelta(hours=1)
            db.session.commit()
            logger.info("Password reset requested for user id %s", user.id)
        # Identical response whether or not the account exists, so the page
        # cannot be used to discover which email addresses are registered.
        return render_template('forgot_password.html', sent=True, email=email)
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
        if len(password) < 8:
            flash('Password must be at least 8 characters.', 'error')
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
