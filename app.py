import sqlite3
from flask import Flask, render_template, request, redirect, url_for, g, session

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_rayoftrust'
DATABASE = 'rayoftrust.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        
        # Create Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                phone TEXT,
                role TEXT NOT NULL DEFAULT 'donor'
            )
        ''')
        
        # Create Donations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS donations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                donor_id INTEGER,
                amount REAL NOT NULL,
                date TEXT NOT NULL,
                purpose TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Received',
                FOREIGN KEY (donor_id) REFERENCES users(id)
            )
        ''')
        
        db.commit()

# Initialize DB on startup
init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] != 'admin' or request.form['password'] != 'admin123':
            error = 'Invalid credentials. Please try again.'
        else:
            session['logged_in'] = True
            return redirect(url_for('admin_dashboard'))
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/donor_login', methods=['GET', 'POST'])
def donor_login():
    error = None
    if request.method == 'POST':
        email = request.form['email']
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ? AND role = 'donor'", (email,))
        user = cursor.fetchone()
        
        if user:
            session['donor_id'] = user['id']
            return redirect(url_for('donor_portal'))
        else:
            error = 'No donor found with that email. Have you made a donation yet?'
            
    return render_template('donor_login.html', error=error)

@app.route('/admin')
def admin_dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    db = get_db()
    cursor = db.cursor()
    # Get active campaigns count
    cursor.execute('SELECT COUNT(DISTINCT purpose) as active_campaigns FROM donations')
    campaigns_row = cursor.fetchone()
    active_campaigns = campaigns_row['active_campaigns'] if campaigns_row['active_campaigns'] else 0
    
    # Get total donors count
    cursor.execute("SELECT COUNT(id) as total_donors_count FROM users WHERE role = 'donor'")
    donors_row = cursor.fetchone()
    total_donors_count = donors_row['total_donors_count'] if donors_row['total_donors_count'] else 0
    
    # Get monthly donation totals for chart
    cursor.execute('''
        SELECT strftime('%m', date) as month_num,
               CASE strftime('%m', date)
                   WHEN '01' THEN 'January' WHEN '02' THEN 'February'
                   WHEN '03' THEN 'March' WHEN '04' THEN 'April'
                   WHEN '05' THEN 'May' WHEN '06' THEN 'June'
                   WHEN '07' THEN 'July' WHEN '08' THEN 'August'
                   WHEN '09' THEN 'September' WHEN '10' THEN 'October'
                   WHEN '11' THEN 'November' WHEN '12' THEN 'December'
               END as month_name,
               SUM(amount) as total
        FROM donations
        GROUP BY month_num, month_name
        ORDER BY month_num ASC
    ''')
    monthly_data = cursor.fetchall()
    chart_labels = [row['month_name'] for row in monthly_data]
    chart_data = [row['total'] for row in monthly_data]
    
    # Get all donations with donor details
    cursor.execute('''
        SELECT d.id, d.amount, d.date, d.purpose, d.status, d.impact_details, u.name as donor_name, u.email as donor_email, u.phone as donor_phone
        FROM donations d
        LEFT JOIN users u ON d.donor_id = u.id
        ORDER BY d.id DESC
    ''')
    donations = cursor.fetchall()
    
    # Get basic stats for the dashboard
    cursor.execute('SELECT SUM(amount) as total FROM donations')
    total_row = cursor.fetchone()
    total_donations = total_row['total'] if total_row['total'] is not None else 0
    
    # Get Top Donors for Leaderboard
    cursor.execute('''
        SELECT u.name as donor_name, SUM(d.amount) as total_contributed
        FROM donations d
        JOIN users u ON d.donor_id = u.id
        GROUP BY u.id
        ORDER BY total_contributed DESC
        LIMIT 3
    ''')
    top_donors = cursor.fetchall()
    
    return render_template('admin.html', donations=donations, total_donations=total_donations, 
                           top_donors=top_donors, active_campaigns=active_campaigns,
                           chart_labels=chart_labels, chart_data=chart_data,
                           total_donors_count=total_donors_count)

@app.route('/donor')
def donor_portal():
    donor_id = session.get('donor_id')
    if not donor_id:
        return redirect(url_for('donor_login'))
        
    db = get_db()
    cursor = db.cursor()
    
    # Get donor info
    cursor.execute('SELECT * FROM users WHERE id = ?', (donor_id,))
    donor = cursor.fetchone()

    # Get this donor's donations
    cursor.execute('SELECT * FROM donations WHERE donor_id = ? ORDER BY date DESC', (donor_id,))
    donations = cursor.fetchall()
    
    return render_template('donor.html', donor=donor, donations=donations)

@app.route('/add_donation', methods=['POST'])
def add_donation():
    if request.method == 'POST':
        donor_name = request.form['donor_name']
        donor_email = request.form['donor_email']
        donor_phone = request.form.get('donor_phone', '').strip()
        if donor_phone == '+91':
            donor_phone = ''
        
        amount = request.form['amount']
        date = request.form['date']
        purpose = request.form['purpose']
        
        db = get_db()
        cursor = db.cursor()
        
        # Check if donor exists by email
        cursor.execute('SELECT id FROM users WHERE email = ?', (donor_email,))
        donor = cursor.fetchone()
        
        if donor:
            donor_id = donor['id']
            # Optionally update phone if it was empty before
            if donor_phone:
                cursor.execute("UPDATE users SET phone = ? WHERE id = ?", (donor_phone, donor_id))
        else:
            # Create new donor
            cursor.execute("INSERT INTO users (name, email, phone, role) VALUES (?, ?, ?, 'donor')", (donor_name, donor_email, donor_phone))
            donor_id = cursor.lastrowid
            
        # Add donation
        cursor.execute("INSERT INTO donations (donor_id, amount, date, purpose, status) VALUES (?, ?, ?, ?, 'Received')",
                       (donor_id, amount, date, purpose))
        db.commit()
        
        return redirect(url_for('admin_dashboard'))

@app.route('/donate')
def public_donate():
    return render_template('donate.html')

@app.route('/thank_you')
def thank_you():
    return render_template('thank_you.html')

@app.route('/public_add_donation', methods=['POST'])
def public_add_donation():
    if request.method == 'POST':
        from datetime import date as dt
        donor_name = request.form['donor_name']
        donor_email = request.form['donor_email']
        amount = request.form['amount']
        purpose = request.form['purpose']
        date = dt.today().strftime('%Y-%m-%d') # Auto-fill today's date
        
        db = get_db()
        cursor = db.cursor()
        
        # Check if donor exists by email
        cursor.execute('SELECT id FROM users WHERE email = ?', (donor_email,))
        donor = cursor.fetchone()
        
        if donor:
            donor_id = donor['id']
        else:
            cursor.execute("INSERT INTO users (name, email, role) VALUES (?, ?, 'donor')", (donor_name, donor_email))
            donor_id = cursor.lastrowid
            
        payment_method = request.form.get('payment_method', 'Online')
        status_string = f"Received (via {payment_method})"
        
        cursor.execute("INSERT INTO donations (donor_id, amount, date, purpose, status) VALUES (?, ?, ?, ?, ?)",
                       (donor_id, amount, date, purpose, status_string))
        db.commit()
        
        return redirect(url_for('thank_you'))

@app.route('/receipt/<int:donation_id>')
def generate_receipt(donation_id):
    db = get_db()
    cursor = db.cursor()
    
    # IDOR Security Fix: Check who is logged in
    admin_logged_in = session.get('logged_in')
    donor_id = session.get('donor_id')
    
    if not admin_logged_in and not donor_id:
        return "Unauthorized: Please log in", 401

    cursor.execute('''
        SELECT d.id, d.amount, d.date, d.purpose, d.donor_id, u.name as donor_name, u.email as donor_email
        FROM donations d
        JOIN users u ON d.donor_id = u.id
        WHERE d.id = ?
    ''', (donation_id,))
    receipt_data = cursor.fetchone()
    
    if not receipt_data:
        return "Receipt not found", 404
        
    # If it's a donor, they can only view THEIR OWN receipt
    if not admin_logged_in and receipt_data['donor_id'] != donor_id:
        return "Unauthorized: This is not your receipt", 403
        
    return render_template('receipt.html', data=receipt_data)

@app.route('/update_status/<int:donation_id>', methods=['POST'])
def update_status(donation_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    new_status = request.form.get('status')
    impact_details = request.form.get('impact_details')
    
    db = get_db()
    cursor = db.cursor()
    
    if impact_details and impact_details.strip():
        cursor.execute('UPDATE donations SET status = ?, impact_details = ? WHERE id = ?', (new_status, impact_details.strip(), donation_id))
    else:
        cursor.execute('UPDATE donations SET status = ? WHERE id = ?', (new_status, donation_id))
        
    db.commit()
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
