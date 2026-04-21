"""
PawCare — Pet Care & Veterinary Management System
Single-template Flask application. All pages live in templates/index.html.

Run with:
    pip install flask werkzeug
    python app.py

Admin: signup with email admin@pawcare.in
"""

import sqlite3
import os
from functools import wraps
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, jsonify
)
from werkzeug.security import generate_password_hash, check_password_hash

# ─────────────────────────────────────────────
# App Configuration
# ─────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = 'super_secret_pawcare_key_2025'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, 'database.db')


# ─────────────────────────────────────────────
# Database Helpers
# ─────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur  = conn.cursor()

    cur.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        phone TEXT DEFAULT '',
        city  TEXT DEFAULT '',
        is_admin INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now'))
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS doctors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        specialization TEXT NOT NULL,
        experience TEXT DEFAULT '',
        qualification TEXT DEFAULT '',
        status TEXT DEFAULT 'available',
        emoji TEXT DEFAULT '🩺',
        rating REAL DEFAULT 5.0,
        bg_color TEXT DEFAULT '#C8DEC9'
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        owner_name TEXT NOT NULL,
        phone TEXT NOT NULL,
        pet_name TEXT NOT NULL,
        pet_type TEXT NOT NULL,
        service TEXT NOT NULL,
        doctor_id INTEGER DEFAULT NULL,
        pref_date TEXT NOT NULL,
        payment_method TEXT NOT NULL,
        description TEXT DEFAULT '',
        status TEXT DEFAULT 'Pending',
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY(user_id)   REFERENCES users(id),
        FOREIGN KEY(doctor_id) REFERENCES doctors(id)
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        appointment_id INTEGER NOT NULL,
        method TEXT NOT NULL,
        status TEXT DEFAULT 'Pending',
        amount REAL DEFAULT 500.0,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY(appointment_id) REFERENCES appointments(id)
    )''')

    conn.commit()

    # Seed doctors if empty
    if conn.execute('SELECT COUNT(*) FROM doctors').fetchone()[0] == 0:
        doctors = [
            ('Dr. Priya Sharma',  'Small Animals & Surgery',    '12 years', 'BVSc, MVSc IVRI',        'available',   '🐕', 5.0, '#C8DEC9'),
            ('Dr. Arjun Mehta',   'Feline Medicine',             '9 years',  'BVSc, Cert. Feline Med.', 'available',   '🐈', 4.9, '#F2D5BC'),
            ('Dr. Kavita Nair',   'Exotic Pets & Avian',         '7 years',  'BVSc, Dip. ECZM',         'available',   '🐦', 5.0, '#EAF3DE'),
            ('Dr. Rohan Desai',   'Nutrition & Dermatology',     '10 years', 'BVSc, PhD Nutrition',     'available',   '🐇', 4.8, '#EEEDFE'),
            ('Dr. Ananya Bose',   'General Veterinary Practice', '6 years',  'BVSc, MVSc',              'unavailable', '🩺', 4.7, '#FDE8E8'),
        ]
        cur.executemany('''INSERT INTO doctors
            (name, specialization, experience, qualification, status, emoji, rating, bg_color)
            VALUES (?,?,?,?,?,?,?,?)''', doctors)
        conn.commit()
    conn.close()


init_db()


# ─────────────────────────────────────────────
# Auth Decorators
# ─────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id'):
            flash('Please log in to continue.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id'):
            flash('Please log in.', 'error')
            return redirect(url_for('login'))
        if not session.get('is_admin'):
            flash('Admin access only.', 'error')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated


# ─────────────────────────────────────────────
# Helper: render with page flag
# ─────────────────────────────────────────────
def render(page, **kwargs):
    """Shortcut to render the single index.html with a page flag."""
    return render_template('index.html', page=page, **kwargs)


# ─────────────────────────────────────────────
# Public Routes
# ─────────────────────────────────────────────
@app.route('/')
def home():
    if not session.get('user_id'):
        return redirect(url_for('login'))
    conn = get_db()
    doctors = conn.execute('SELECT * FROM doctors ORDER BY status DESC, rating DESC').fetchall()
    conn.close()
    return render('home', doctors=doctors)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id'):
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password'], password):
            session['user_id']   = user['id']
            session['user_name'] = user['name']
            session['is_admin']  = bool(user['is_admin'])
            flash(f'Welcome back, {user["name"]}! 🐾', 'success')
            return redirect(url_for('admin') if user['is_admin'] else url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'error')

    return render('login')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if session.get('user_id'):
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        name     = request.form.get('name', '').strip()
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not name or not email or not password:
            flash('All fields are required.', 'error')
            return redirect(url_for('signup'))
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'error')
            return redirect(url_for('signup'))

        hashed   = generate_password_hash(password, method='pbkdf2:sha256')
        is_admin = 1 if email == 'admin@pawcare.in' else 0
        try:
            conn = get_db()
            conn.execute('INSERT INTO users (name, email, password, is_admin) VALUES (?,?,?,?)',
                         (name, email, hashed, is_admin))
            conn.commit()
            conn.close()
            flash('Account created! Please log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Email already registered.', 'error')
            return redirect(url_for('signup'))

    return render('signup')


@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out. See you soon! 🐾', 'info')
    return redirect(url_for('login'))


# ─────────────────────────────────────────────
# User Routes
# ─────────────────────────────────────────────
@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    uid  = session['user_id']
    total     = conn.execute('SELECT COUNT(*) FROM appointments WHERE user_id=?', (uid,)).fetchone()[0]
    pending   = conn.execute("SELECT COUNT(*) FROM appointments WHERE user_id=? AND status='Pending'",   (uid,)).fetchone()[0]
    confirmed = conn.execute("SELECT COUNT(*) FROM appointments WHERE user_id=? AND status='Confirmed'", (uid,)).fetchone()[0]
    completed = conn.execute("SELECT COUNT(*) FROM appointments WHERE user_id=? AND status='Completed'", (uid,)).fetchone()[0]
    recent    = conn.execute('''
        SELECT a.*, d.name AS doctor_name FROM appointments a
        LEFT JOIN doctors d ON a.doctor_id = d.id
        WHERE a.user_id=? ORDER BY a.id DESC LIMIT 5
    ''', (uid,)).fetchall()
    doctors = conn.execute("SELECT * FROM doctors WHERE status='available' ORDER BY rating DESC").fetchall()
    conn.close()
    return render('dashboard',
        total=total, pending=pending, confirmed=confirmed,
        completed=completed, recent=recent, doctors=doctors)


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    conn = get_db()
    uid  = session['user_id']
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'update_profile':
            name  = request.form.get('name', '').strip()
            phone = request.form.get('phone', '').strip()
            city  = request.form.get('city',  '').strip()
            if not name:
                flash('Name cannot be empty.', 'error')
            else:
                conn.execute('UPDATE users SET name=?, phone=?, city=? WHERE id=?', (name, phone, city, uid))
                conn.commit()
                session['user_name'] = name
                flash('Profile updated!', 'success')
        elif action == 'change_password':
            old_pw = request.form.get('old_password', '')
            new_pw = request.form.get('new_password', '')
            user   = conn.execute('SELECT * FROM users WHERE id=?', (uid,)).fetchone()
            if not check_password_hash(user['password'], old_pw):
                flash('Current password incorrect.', 'error')
            elif len(new_pw) < 6:
                flash('New password must be 6+ characters.', 'error')
            else:
                conn.execute('UPDATE users SET password=? WHERE id=?',
                             (generate_password_hash(new_pw, method='pbkdf2:sha256'), uid))
                conn.commit()
                flash('Password changed!', 'success')
        conn.close()
        return redirect(url_for('profile'))

    user  = conn.execute('SELECT * FROM users WHERE id=?', (uid,)).fetchone()
    total = conn.execute('SELECT COUNT(*) FROM appointments WHERE user_id=?', (uid,)).fetchone()[0]
    conn.close()
    return render('profile', user=user, total=total)


@app.route('/appointments')
@login_required
def appointments():
    conn  = get_db()
    uid   = session['user_id']
    appts = conn.execute('''
        SELECT a.*, d.name AS doctor_name, p.status AS payment_status
        FROM appointments a
        LEFT JOIN doctors  d ON a.doctor_id = d.id
        LEFT JOIN payments p ON p.appointment_id = a.id
        WHERE a.user_id=? ORDER BY a.id DESC
    ''', (uid,)).fetchall()
    conn.close()
    return render('appointments', appts=appts)


# ─────────────────────────────────────────────
# Booking Routes
# ─────────────────────────────────────────────
@app.route('/book', methods=['POST'])
@login_required
def book():
    uid            = session['user_id']
    owner_name     = request.form.get('owner_name', '').strip()
    phone          = request.form.get('phone', '').strip()
    pet_name       = request.form.get('pet_name', '').strip()
    pet_type       = request.form.get('pet_type', '')
    service        = request.form.get('service', '')
    doctor_id      = request.form.get('doctor_id') or None
    pref_date      = request.form.get('pref_date', '')
    payment_method = request.form.get('payment_method', 'clinic')
    description    = request.form.get('description', '').strip()

    if not all([owner_name, phone, pet_name, pet_type, service, pref_date]):
        flash('Please fill all required fields.', 'error')
        return redirect(url_for('home') + '#book')

    conn = get_db()
    cur  = conn.cursor()
    cur.execute('''INSERT INTO appointments
        (user_id, owner_name, phone, pet_name, pet_type, service,
         doctor_id, pref_date, payment_method, description, status)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
        (uid, owner_name, phone, pet_name, pet_type, service,
         doctor_id, pref_date, payment_method, description, 'Pending'))
    appt_id = cur.lastrowid
    pay_status = 'Paid' if payment_method == 'clinic' else 'Pending'
    cur.execute('INSERT INTO payments (appointment_id, method, status) VALUES (?,?,?)',
                (appt_id, payment_method, pay_status))
    conn.commit()
    conn.close()
    session['last_appt_id'] = appt_id

    if payment_method == 'clinic':
        return redirect(url_for('success'))
    return redirect(url_for('payment', method=payment_method, appt_id=appt_id))


@app.route('/payment/<method>')
@login_required
def payment(method):
    appt_id = request.args.get('appt_id', session.get('last_appt_id'))
    return render('payment', method=method, appt_id=appt_id)


@app.route('/payment/process', methods=['POST'])
@login_required
def process_payment():
    appt_id = request.form.get('appt_id')
    if appt_id:
        conn = get_db()
        conn.execute("UPDATE payments     SET status='Paid'      WHERE appointment_id=?", (appt_id,))
        conn.execute("UPDATE appointments SET status='Confirmed' WHERE id=?",             (appt_id,))
        conn.commit()
        conn.close()
        session['last_appt_id'] = appt_id
    flash('Payment successful! Appointment confirmed. 🎉', 'success')
    return redirect(url_for('success'))


@app.route('/success')
@login_required
def success():
    appt_id = session.get('last_appt_id')
    appt = None
    if appt_id:
        conn = get_db()
        appt = conn.execute('''
            SELECT a.*, d.name AS doctor_name FROM appointments a
            LEFT JOIN doctors d ON a.doctor_id = d.id WHERE a.id=?
        ''', (appt_id,)).fetchone()
        conn.close()
    return render('success', appt=appt)


# ─────────────────────────────────────────────
# AJAX
# ─────────────────────────────────────────────
@app.route('/api/doctors')
def api_doctors():
    spec = request.args.get('specialization', '')
    conn = get_db()
    if spec and spec != 'All':
        rows = conn.execute(
            "SELECT * FROM doctors WHERE specialization LIKE ? ORDER BY status DESC, rating DESC",
            (f'%{spec}%',)).fetchall()
    else:
        rows = conn.execute('SELECT * FROM doctors ORDER BY status DESC, rating DESC').fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


# ─────────────────────────────────────────────
# Admin Routes
# ─────────────────────────────────────────────
@app.route('/admin')
@admin_required
def admin():
    conn = get_db()
    total_users   = conn.execute('SELECT COUNT(*) FROM users WHERE is_admin=0').fetchone()[0]
    total_appts   = conn.execute('SELECT COUNT(*) FROM appointments').fetchone()[0]
    total_doctors = conn.execute('SELECT COUNT(*) FROM doctors').fetchone()[0]
    total_paid    = conn.execute("SELECT COUNT(*) FROM payments WHERE status='Paid'").fetchone()[0]
    pending_appts = conn.execute("SELECT COUNT(*) FROM appointments WHERE status='Pending'").fetchone()[0]
    appointments  = conn.execute('''
        SELECT a.*, d.name AS doctor_name, u.name AS user_name,
               p.status AS payment_status
        FROM appointments a
        LEFT JOIN doctors  d ON a.doctor_id = d.id
        LEFT JOIN users    u ON a.user_id   = u.id
        LEFT JOIN payments p ON p.appointment_id = a.id
        ORDER BY a.id DESC LIMIT 20
    ''').fetchall()
    users   = conn.execute('SELECT * FROM users   ORDER BY id DESC').fetchall()
    doctors = conn.execute('SELECT * FROM doctors ORDER BY id').fetchall()
    conn.close()
    return render('admin',
        total_users=total_users, total_appts=total_appts,
        total_doctors=total_doctors, total_paid=total_paid,
        pending_appts=pending_appts,
        appointments=appointments, users=users, doctors=doctors)


@app.route('/update_appointment_status/<int:appt_id>', methods=['POST'])
@admin_required
def update_appointment_status(appt_id):
    status = request.form.get('status')
    if status in ('Pending', 'Confirmed', 'Completed', 'Cancelled'):
        conn = get_db()
        conn.execute('UPDATE appointments SET status=? WHERE id=?', (status, appt_id))
        conn.commit()
        conn.close()
        flash(f'Appointment #{appt_id} → {status}', 'success')
    return redirect(url_for('admin'))


@app.route('/add_doctor', methods=['GET', 'POST'])
@admin_required
def add_doctor():
    if request.method == 'POST':
        name   = request.form.get('name', '').strip()
        spec   = request.form.get('specialization', '').strip()
        exp    = request.form.get('experience', '').strip()
        qual   = request.form.get('qualification', '').strip()
        status = request.form.get('status', 'available')
        emoji  = request.form.get('emoji', '🩺').strip()
        rating = float(request.form.get('rating', 5.0))
        bg     = request.form.get('bg_color', '#C8DEC9').strip()
        if not name or not spec:
            flash('Name and specialization required.', 'error')
            return redirect(url_for('add_doctor'))
        conn = get_db()
        conn.execute('''INSERT INTO doctors
            (name, specialization, experience, qualification, status, emoji, rating, bg_color)
            VALUES (?,?,?,?,?,?,?,?)''', (name, spec, exp, qual, status, emoji, rating, bg))
        conn.commit()
        conn.close()
        flash(f'{name} added!', 'success')
        return redirect(url_for('admin'))
    return render('add_doctor')


@app.route('/edit_doctor/<int:doc_id>', methods=['GET', 'POST'])
@admin_required
def edit_doctor(doc_id):
    conn   = get_db()
    doctor = conn.execute('SELECT * FROM doctors WHERE id=?', (doc_id,)).fetchone()
    if not doctor:
        flash('Doctor not found.', 'error')
        conn.close()
        return redirect(url_for('admin'))
    if request.method == 'POST':
        name   = request.form.get('name', '').strip()
        spec   = request.form.get('specialization', '').strip()
        exp    = request.form.get('experience', '').strip()
        qual   = request.form.get('qualification', '').strip()
        status = request.form.get('status', 'available')
        emoji  = request.form.get('emoji', '🩺').strip()
        rating = float(request.form.get('rating', 5.0))
        bg     = request.form.get('bg_color', '#C8DEC9').strip()
        conn.execute('''UPDATE doctors SET name=?,specialization=?,experience=?,qualification=?,
                        status=?,emoji=?,rating=?,bg_color=? WHERE id=?''',
                     (name, spec, exp, qual, status, emoji, rating, bg, doc_id))
        conn.commit()
        conn.close()
        flash('Doctor updated!', 'success')
        return redirect(url_for('admin'))
    conn.close()
    return render('edit_doctor', doctor=doctor)


@app.route('/delete_doctor/<int:doc_id>', methods=['POST'])
@admin_required
def delete_doctor(doc_id):
    conn = get_db()
    conn.execute('DELETE FROM doctors WHERE id=?', (doc_id,))
    conn.commit()
    conn.close()
    flash('Doctor removed.', 'success')
    return redirect(url_for('admin'))


@app.route('/toggle_doctor/<int:doc_id>', methods=['POST'])
@admin_required
def toggle_doctor(doc_id):
    conn   = get_db()
    doctor = conn.execute('SELECT status FROM doctors WHERE id=?', (doc_id,)).fetchone()
    if doctor:
        new = 'unavailable' if doctor['status'] == 'available' else 'available'
        conn.execute('UPDATE doctors SET status=? WHERE id=?', (new, doc_id))
        conn.commit()
        flash(f'Doctor status → {new}', 'success')
    conn.close()
    return redirect(url_for('admin'))


# ─────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
