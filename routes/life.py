from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from models import db, Vehicle, HealthRecord
from datetime import datetime, date, timedelta

life = Blueprint('life', __name__)

# We'll add extra models inline using db directly
from flask_sqlalchemy import SQLAlchemy
from models import db as _db

# ===== VEHICLE =====
@life.route('/vehicle')
@login_required
def vehicle():
    from models import Vehicle
    today = date.today()
    vehicles = Vehicle.query.filter_by(user_id=current_user.id).all()
    fuel_logs = FuelLog.query.filter_by(user_id=current_user.id).order_by(FuelLog.date.desc()).limit(20).all()
    return render_template('vehicle.html', vehicles=vehicles, fuel_logs=fuel_logs, today=today)

@life.route('/vehicle/add', methods=['POST'])
@login_required
def add_vehicle():
    data = request.get_json()
    try:
        v = Vehicle(
            user_id=current_user.id,
            name=data['name'],
            registration_number=data.get('registration_number', ''),
            insurance_expiry=datetime.strptime(data['insurance_expiry'], '%Y-%m-%d').date() if data.get('insurance_expiry') else None,
            puc_expiry=datetime.strptime(data['puc_expiry'], '%Y-%m-%d').date() if data.get('puc_expiry') else None,
            last_service_date=datetime.strptime(data['last_service_date'], '%Y-%m-%d').date() if data.get('last_service_date') else None,
            next_service_km=int(data.get('next_service_km') or 0) or None,
            current_km=int(data.get('current_km') or 0) or None,
            notes=data.get('notes', '')
        )
        db.session.add(v)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@life.route('/vehicle/delete/<int:id>', methods=['POST'])
@login_required
def delete_vehicle(id):
    v = Vehicle.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(v)
    db.session.commit()
    return jsonify({'success': True})

@life.route('/vehicle/fuel/add', methods=['POST'])
@login_required
def add_fuel():
    data = request.get_json()
    try:
        log = FuelLog(
            user_id=current_user.id,
            vehicle_id=int(data.get('vehicle_id', 0)) or None,
            amount=float(data['amount']),
            litres=float(data.get('litres') or 0) or None,
            km_reading=int(data.get('km_reading') or 0) or None,
            date=datetime.strptime(data.get('date', date.today().isoformat()), '%Y-%m-%d').date(),
            notes=data.get('notes', '')
        )
        db.session.add(log)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@life.route('/vehicle/fuel/delete/<int:id>', methods=['POST'])
@login_required
def delete_fuel(id):
    log = FuelLog.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(log)
    db.session.commit()
    return jsonify({'success': True})

# ===== HEALTH =====
@life.route('/health')
@login_required
def health():
    records = HealthRecord.query.filter_by(user_id=current_user.id).order_by(HealthRecord.date.desc()).all()
    total_medical_expense = sum(r.amount for r in records if r.amount)
    return render_template('health.html', records=records, total_medical_expense=total_medical_expense)

@life.route('/health/add', methods=['POST'])
@login_required
def add_health():
    data = request.get_json()
    try:
        r = HealthRecord(
            user_id=current_user.id,
            record_type=data.get('record_type', 'Doctor Visit'),
            title=data['title'],
            amount=float(data.get('amount') or 0),
            date=datetime.strptime(data.get('date', date.today().isoformat()), '%Y-%m-%d').date(),
            doctor_name=data.get('doctor_name', ''),
            notes=data.get('notes', '')
        )
        db.session.add(r)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@life.route('/health/delete/<int:id>', methods=['POST'])
@login_required
def delete_health(id):
    r = HealthRecord.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(r)
    db.session.commit()
    return jsonify({'success': True})

# ===== HOME MAINTENANCE =====
@life.route('/home-maintenance')
@login_required
def home_maintenance():
    tasks = HomeTask.query.filter_by(user_id=current_user.id).order_by(HomeTask.next_due.asc()).all()
    logs = HomeLog.query.filter_by(user_id=current_user.id).order_by(HomeLog.date.desc()).limit(20).all()
    today = date.today()
    return render_template('home_maintenance.html', tasks=tasks, logs=logs, today=today)

@life.route('/home-maintenance/task/add', methods=['POST'])
@login_required
def add_home_task():
    data = request.get_json()
    try:
        t = HomeTask(
            user_id=current_user.id,
            title=data['title'],
            frequency_days=int(data.get('frequency_days') or 0) or None,
            next_due=datetime.strptime(data['next_due'], '%Y-%m-%d').date() if data.get('next_due') else None,
            contact_name=data.get('contact_name', ''),
            contact_phone=data.get('contact_phone', ''),
            notes=data.get('notes', '')
        )
        db.session.add(t)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@life.route('/home-maintenance/task/done/<int:id>', methods=['POST'])
@login_required
def mark_task_done(id):
    t = HomeTask.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    if t.frequency_days:
        t.next_due = date.today() + timedelta(days=t.frequency_days)
    t.last_done = date.today()
    db.session.commit()
    return jsonify({'success': True})

@life.route('/home-maintenance/task/delete/<int:id>', methods=['POST'])
@login_required
def delete_home_task(id):
    t = HomeTask.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(t)
    db.session.commit()
    return jsonify({'success': True})

@life.route('/home-maintenance/log/add', methods=['POST'])
@login_required
def add_home_log():
    data = request.get_json()
    try:
        log = HomeLog(
            user_id=current_user.id,
            title=data['title'],
            amount=float(data.get('amount') or 0),
            date=datetime.strptime(data.get('date', date.today().isoformat()), '%Y-%m-%d').date(),
            notes=data.get('notes', '')
        )
        db.session.add(log)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@life.route('/home-maintenance/log/delete/<int:id>', methods=['POST'])
@login_required
def delete_home_log(id):
    log = HomeLog.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(log)
    db.session.commit()
    return jsonify({'success': True})

# ===== GAS CYLINDER =====
@life.route('/gas')
@login_required
def gas():
    logs = GasLog.query.filter_by(user_id=current_user.id).order_by(GasLog.date.desc()).all()
    total_spent = sum(g.amount for g in logs)
    avg_days = 0
    if len(logs) >= 2:
        gaps = [(logs[i].date - logs[i+1].date).days for i in range(len(logs)-1)]
        avg_days = round(sum(gaps) / len(gaps))
    next_est = date.today() + timedelta(days=avg_days) if avg_days else None
    return render_template('gas.html', logs=logs, total_spent=total_spent, avg_days=avg_days, next_est=next_est)

@life.route('/gas/add', methods=['POST'])
@login_required
def add_gas():
    data = request.get_json()
    try:
        log = GasLog(
            user_id=current_user.id,
            amount=float(data.get('amount') or 0),
            date=datetime.strptime(data.get('date', date.today().isoformat()), '%Y-%m-%d').date(),
            notes=data.get('notes', '')
        )
        db.session.add(log)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@life.route('/gas/delete/<int:id>', methods=['POST'])
@login_required
def delete_gas(id):
    log = GasLog.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(log)
    db.session.commit()
    return jsonify({'success': True})

# ===== TRIP BUDGET =====
@life.route('/trips')
@login_required
def trips():
    all_trips = Trip.query.filter_by(user_id=current_user.id).order_by(Trip.start_date.desc()).all()
    return render_template('trips.html', trips=all_trips)

@life.route('/trips/add', methods=['POST'])
@login_required
def add_trip():
    data = request.get_json()
    try:
        trip = Trip(
            user_id=current_user.id,
            name=data['name'],
            destination=data.get('destination', ''),
            budget=float(data.get('budget') or 0),
            start_date=datetime.strptime(data['start_date'], '%Y-%m-%d').date() if data.get('start_date') else date.today(),
            end_date=datetime.strptime(data['end_date'], '%Y-%m-%d').date() if data.get('end_date') else None,
            notes=data.get('notes', '')
        )
        db.session.add(trip)
        db.session.commit()
        return jsonify({'success': True, 'id': trip.id})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@life.route('/trips/<int:id>')
@login_required
def trip_detail(id):
    trip = Trip.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    expenses = TripExpense.query.filter_by(trip_id=id).order_by(TripExpense.date.desc()).all()
    total_spent = sum(e.amount for e in expenses)
    remaining = trip.budget - total_spent if trip.budget else 0
    return render_template('trip_detail.html', trip=trip, expenses=expenses,
                           total_spent=total_spent, remaining=remaining)

@life.route('/trips/<int:id>/expense/add', methods=['POST'])
@login_required
def add_trip_expense(id):
    trip = Trip.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    data = request.get_json()
    try:
        exp = TripExpense(
            trip_id=id,
            category=data.get('category', 'Other'),
            description=data.get('description', ''),
            amount=float(data['amount']),
            date=datetime.strptime(data.get('date', date.today().isoformat()), '%Y-%m-%d').date()
        )
        db.session.add(exp)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@life.route('/trips/expense/delete/<int:id>', methods=['POST'])
@login_required
def delete_trip_expense(id):
    exp = TripExpense.query.get_or_404(id)
    db.session.delete(exp)
    db.session.commit()
    return jsonify({'success': True})

@life.route('/trips/delete/<int:id>', methods=['POST'])
@login_required
def delete_trip(id):
    trip = Trip.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    TripExpense.query.filter_by(trip_id=id).delete()
    db.session.delete(trip)
    db.session.commit()
    return jsonify({'success': True})

# ===== EXTRA MODELS (defined here for Part 3) =====
class FuelLog(db.Model):
    __tablename__ = 'fuel_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'), nullable=True)
    amount = db.Column(db.Float, nullable=False)
    litres = db.Column(db.Float)
    km_reading = db.Column(db.Integer)
    date = db.Column(db.Date, default=date.today)
    notes = db.Column(db.Text)

class HomeTask(db.Model):
    __tablename__ = 'home_tasks'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    frequency_days = db.Column(db.Integer)
    next_due = db.Column(db.Date)
    last_done = db.Column(db.Date)
    contact_name = db.Column(db.String(100))
    contact_phone = db.Column(db.String(20))
    notes = db.Column(db.Text)

class HomeLog(db.Model):
    __tablename__ = 'home_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, default=0)
    date = db.Column(db.Date, default=date.today)
    notes = db.Column(db.Text)

class GasLog(db.Model):
    __tablename__ = 'gas_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Float, default=0)
    date = db.Column(db.Date, default=date.today)
    notes = db.Column(db.Text)

class Trip(db.Model):
    __tablename__ = 'trips'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    destination = db.Column(db.String(100))
    budget = db.Column(db.Float, default=0)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    notes = db.Column(db.Text)

class TripExpense(db.Model):
    __tablename__ = 'trip_expenses'
    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.Integer, db.ForeignKey('trips.id'), nullable=False)
    category = db.Column(db.String(50))
    description = db.Column(db.String(200))
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, default=date.today)
