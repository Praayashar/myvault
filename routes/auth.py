from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User

# Python 3.9 on Mac does not support scrypt — use pbkdf2
HASH_METHOD = "pbkdf2:sha256"

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
    # Only allow if no users exist (first-time setup) or admin
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
            name=name,
            email=email,
            password_hash=generate_password_hash(password, method=HASH_METHOD),
            role=role
        )
        db.session.add(user)
        db.session.commit()
        if user_count == 0:
            login_user(user)
            flash(f'Welcome to MyVault, {name}! Add the second profile for your father.', 'success')
            return redirect(url_for('main.dashboard'))
        flash('Profile created successfully!', 'success')
        return redirect(url_for('main.dashboard'))
    return render_template('register.html', first_setup=(user_count == 0))

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))