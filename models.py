from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='member')  # 'admin' or 'member'
    simple_mode = db.Column(db.Boolean, default=False)
    reset_token = db.Column(db.String(100), nullable=True)
    reset_token_expiry = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    expenses = db.relationship('Expense', backref='user', lazy=True)
    incomes = db.relationship('Income', backref='user', lazy=True)
    subscriptions = db.relationship('Subscription', backref='user', lazy=True)
    emis = db.relationship('EMI', backref='user', lazy=True)
    investments = db.relationship('Investment', backref='user', lazy=True)
    savings_goals = db.relationship('SavingsGoal', backref='user', lazy=True)
    passwords = db.relationship('PasswordVault', backref='user', lazy=True)
    vehicles = db.relationship('Vehicle', backref='user', lazy=True)
    health_records = db.relationship('HealthRecord', backref='user', lazy=True)
    notices = db.relationship('FamilyNotice', backref='user', lazy=True)
    important_dates = db.relationship('ImportantDate', backref='user', lazy=True)

class Expense(db.Model):
    __tablename__ = 'expenses'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    payment_method = db.Column(db.String(30), default='UPI')
    description = db.Column(db.String(200))
    notes = db.Column(db.Text)
    date = db.Column(db.Date, default=datetime.utcnow().date)
    is_recurring = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Income(db.Model):
    __tablename__ = 'incomes'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    source = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200))
    date = db.Column(db.Date, default=datetime.utcnow().date)
    is_recurring = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Subscription(db.Model):
    __tablename__ = 'subscriptions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    billing_cycle = db.Column(db.String(20), default='monthly')
    renewal_date = db.Column(db.Date, nullable=False)
    category = db.Column(db.String(50))
    reminder_sent = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class EMI(db.Model):
    __tablename__ = 'emis'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    emi_amount = db.Column(db.Float, nullable=False)
    total_installments = db.Column(db.Integer, nullable=False)
    paid_installments = db.Column(db.Integer, default=0)
    due_date = db.Column(db.Integer)  # day of month
    start_date = db.Column(db.Date)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Investment(db.Model):
    __tablename__ = 'investments'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # FD, RD, MF
    name = db.Column(db.String(100), nullable=False)
    principal = db.Column(db.Float, nullable=False)
    interest_rate = db.Column(db.Float)
    start_date = db.Column(db.Date)
    maturity_date = db.Column(db.Date)
    maturity_amount = db.Column(db.Float)
    bank_name = db.Column(db.String(100))
    notes = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class SavingsGoal(db.Model):
    __tablename__ = 'savings_goals'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    target_amount = db.Column(db.Float, nullable=False)
    current_amount = db.Column(db.Float, default=0)
    target_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class BudgetLimit(db.Model):
    __tablename__ = 'budget_limits'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    monthly_limit = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PasswordVault(db.Model):
    __tablename__ = 'password_vault'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    app_name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), default='Other')
    username = db.Column(db.String(150))
    email = db.Column(db.String(150))
    password = db.Column(db.String(256), nullable=False)
    website_url = db.Column(db.String(200))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AccountDirectory(db.Model):
    __tablename__ = 'account_directory'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    account_type = db.Column(db.String(50))  # Bank, Demat, etc.
    account_name = db.Column(db.String(100), nullable=False)
    account_number = db.Column(db.String(100))
    ifsc_code = db.Column(db.String(20))
    branch = db.Column(db.String(100))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class DocumentVault(db.Model):
    __tablename__ = 'document_vault'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    doc_type = db.Column(db.String(50))  # Aadhar, PAN, Passport etc.
    doc_name = db.Column(db.String(100), nullable=False)
    doc_number = db.Column(db.String(100))
    expiry_date = db.Column(db.Date)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Vehicle(db.Model):
    __tablename__ = 'vehicles'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    registration_number = db.Column(db.String(30))
    insurance_expiry = db.Column(db.Date)
    puc_expiry = db.Column(db.Date)
    last_service_date = db.Column(db.Date)
    next_service_km = db.Column(db.Integer)
    current_km = db.Column(db.Integer)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class HealthRecord(db.Model):
    __tablename__ = 'health_records'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    record_type = db.Column(db.String(50))  # Doctor Visit, Medicine, etc.
    title = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, default=0)
    date = db.Column(db.Date)
    doctor_name = db.Column(db.String(100))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class FamilyNotice(db.Model):
    __tablename__ = 'family_notices'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_pinned = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ImportantDate(db.Model):
    __tablename__ = 'important_dates'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date, nullable=False)
    type = db.Column(db.String(30))  # Birthday, Anniversary, etc.
    reminder_days = db.Column(db.Integer, default=3)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Insurance(db.Model):
    __tablename__ = 'insurance'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    type = db.Column(db.String(50))  # Life, Health, Vehicle, Home
    provider = db.Column(db.String(100), nullable=False)
    policy_number = db.Column(db.String(100))
    premium_amount = db.Column(db.Float)
    premium_due_date = db.Column(db.Date)
    sum_insured = db.Column(db.Float)
    nominee = db.Column(db.String(100))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
