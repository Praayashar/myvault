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


# ===========================================================================
# ReminderLog - records that a reminder has already been sent, for ANY record
# type. Previously only Subscription had a `reminder_sent` flag, so insurance,
# EMI, vehicle papers, documents and maturities could never be tracked.
# This is a NEW table, so db.create_all() adds it with no migration needed.
# ===========================================================================
class ReminderLog(db.Model):
    __tablename__ = 'reminder_log'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    record_type = db.Column(db.String(40), nullable=False)   # 'subscription', 'insurance', ...
    record_id = db.Column(db.Integer, nullable=False)
    due_date = db.Column(db.Date, nullable=False)            # the date being reminded about
    sent_on = db.Column(db.Date, nullable=False, default=lambda: datetime.utcnow().date())
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.Index('ix_reminder_unique', 'record_type', 'record_id', 'due_date'),
    )


# ===========================================================================
# LoginAttempt - rate limiting for the login page. A new table rather than new
# columns on `users`, so no ALTER TABLE is needed on the live database.
# ===========================================================================
class LoginAttempt(db.Model):
    __tablename__ = 'login_attempts'
    id = db.Column(db.Integer, primary_key=True)
    identifier = db.Column(db.String(200), nullable=False, index=True)  # email or IP
    attempted_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    successful = db.Column(db.Boolean, default=False)


# ===========================================================================
# BusinessExpense - Raw to Ready's books, kept deliberately separate from
# personal expenses.
#
# A separate table rather than a flag on Expense, for three reasons:
#   1. New tables are created by db.create_all() with no migration risk.
#   2. Business entries carry GST fields that make no sense on a grocery bill.
#   3. The Family page aggregates Expense only, so business spending stays
#      out of the view other family members can see.
# ===========================================================================
class BusinessExpense(db.Model):
    __tablename__ = 'business_expenses'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    date = db.Column(db.Date, nullable=False, default=lambda: datetime.utcnow().date())
    vendor_name = db.Column(db.String(200), nullable=False)
    vendor_gstin = db.Column(db.String(20))          # 15 chars when present
    invoice_number = db.Column(db.String(60))
    category = db.Column(db.String(60), nullable=False)

    # GST breakdown. taxable_value is the pre-tax amount; total is what left
    # the bank. Intra-state splits into CGST+SGST, inter-state goes to IGST.
    taxable_value = db.Column(db.Float, nullable=False, default=0)
    gst_rate = db.Column(db.Float, default=0)        # 0, 5, 12, 18, 28
    supply_type = db.Column(db.String(12), default='intra')   # intra | inter | none
    cgst = db.Column(db.Float, default=0)
    sgst = db.Column(db.Float, default=0)
    igst = db.Column(db.Float, default=0)
    total_amount = db.Column(db.Float, nullable=False, default=0)

    payment_mode = db.Column(db.String(30))
    # Whether this GST can be claimed back as input credit. Not everything can -
    # personal-use items and blocked credits under Section 17(5) cannot.
    claim_input_credit = db.Column(db.Boolean, default=True)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def gst_amount(self):
        return (self.cgst or 0) + (self.sgst or 0) + (self.igst or 0)

    @property
    def financial_quarter(self):
        """Indian FY quarter label, matching QRMP filing periods."""
        if not self.date:
            return ''
        m = self.date.month
        if m in (4, 5, 6):
            return f"Q1 Apr-Jun {self.date.year}"
        if m in (7, 8, 9):
            return f"Q2 Jul-Sep {self.date.year}"
        if m in (10, 11, 12):
            return f"Q3 Oct-Dec {self.date.year}"
        return f"Q4 Jan-Mar {self.date.year}"
