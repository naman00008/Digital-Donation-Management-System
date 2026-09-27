import sqlite3
import os
import hmac
import hashlib
import time
import requests
from datetime import datetime, date
from flask import Flask, render_template, request, redirect, url_for, g, session, jsonify, flash
from werkzeug.security import check_password_hash, generate_password_hash
from dotenv import load_dotenv
import stripe
from ai_assistant import generate_ai_response

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'super_secret_key_for_rayoftrust')
DATABASE = 'rayoftrust.db'

# Payment Gateway Configurations
RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', '').strip()
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', '').strip()
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '').strip()
stripe.api_key = STRIPE_SECRET_KEY

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE, timeout=30.0)
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
                password_hash TEXT,
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
                impact_details TEXT,
                FOREIGN KEY (donor_id) REFERENCES users(id)
            )
        ''')

        # Create Celebrations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS celebrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                donor_name TEXT NOT NULL,
                donor_email TEXT NOT NULL,
                donor_phone TEXT,
                occasion_type TEXT NOT NULL,
                celebrant_name TEXT NOT NULL,
                celebration_date TEXT NOT NULL,
                time_slot TEXT NOT NULL,
                package_type TEXT NOT NULL,
                amount REAL NOT NULL,
                attendance_mode TEXT NOT NULL,
                special_message TEXT,
                status TEXT NOT NULL DEFAULT 'Confirmed',
                created_at TEXT NOT NULL,
                payment_method TEXT DEFAULT 'UPI QR Code (namanmtj2005-2@okicici)',
                shelter_kid_id INTEGER,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        try:
            cursor.execute('ALTER TABLE celebrations ADD COLUMN payment_method TEXT DEFAULT "UPI QR Code (namanmtj2005-2@okicici)"')
        except Exception:
            pass
            
        try:
            cursor.execute('ALTER TABLE celebrations ADD COLUMN shelter_kid_id INTEGER')
        except Exception:
            pass

        try:
            cursor.execute('ALTER TABLE donations ADD COLUMN payment_id TEXT')
        except Exception:
            pass
        try:
            cursor.execute('ALTER TABLE donations ADD COLUMN order_id TEXT')
        except Exception:
            pass
        try:
            cursor.execute('ALTER TABLE donations ADD COLUMN utr_number TEXT')
        except Exception:
            pass

        # Create Shelter Kids table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS shelter_kids (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                dob TEXT NOT NULL,
                age INTEGER NOT NULL,
                gender TEXT NOT NULL,
                dream_aspiration TEXT,
                favorite_treat TEXT,
                avatar_color TEXT,
                hobbies TEXT
            )
        ''')
        
        # Check and seed Marathi shelter kids aged 5 to 18
        cursor.execute('SELECT COUNT(*) as count FROM shelter_kids')
        if cursor.fetchone()['count'] == 0:
            marathi_kids = [
                ("Aarohi Shinde", "2019-10-12", 7, "Girl", "Loves drawing and wants to be an art teacher", "Strawberry Cake & Gulab Jamun", "#ff6b6b", "Painting, Crafting"),
                ("Omkar Patil", "2015-11-04", 11, "Boy", "Loves cricket and aspires to be an engineer", "Chocolate Truffle Cake", "#4dabf7", "Cricket, Science Models"),
                ("Tanvi Jadhav", "2017-09-28", 9, "Girl", "Loves traditional Lavani dancing & storytelling", "Pineapple Cake & Kaju Katli", "#f06595", "Dance, Reading"),
                ("Sai Kulkarni", "2020-10-25", 6, "Boy", "Loves playing with building blocks & toy trucks", "Black Forest Cake", "#38d9a9", "Building Blocks, Puzzles"),
                ("Vedant Kadam", "2012-12-02", 14, "Boy", "Aspires to join the Indian Armed Forces", "Butterscotch Cake & Samosas", "#20c997", "Football, Running"),
                ("Ananya Deshmukh", "2014-10-18", 12, "Girl", "Loves biology and wants to be a children's doctor", "Mango Delight Cake", "#da77f2", "Science, Gardening"),
                ("Atharva Chavan", "2018-11-15", 8, "Boy", "Loves singing Marathi bhajans & playing harmonium", "Chocolate Fudge Cake", "#ffa94d", "Music, Singing"),
                ("Swara Joshi", "2021-10-08", 5, "Girl", "Loves coloring storybooks & reciting cute poems", "Vanilla Rainbow Cake", "#ff922b", "Coloring, Rhymes"),
                ("Shaurya More", "2013-11-22", 13, "Boy", "Passionate about mathematics and volleyball", "Choco Lava Cake", "#748ffc", "Math Puzzles, Volleyball"),
                ("Prajakta Gaikwad", "2010-12-10", 16, "Girl", "Studying diligently to become a civil services officer", "Red Velvet Cake", "#e64980", "History, Debate"),
                ("Tejas Bhosale", "2016-10-30", 10, "Boy", "Loves origami and creating handmade greetings", "Caramel Crunch Cake", "#3bc9db", "Origami, Chess"),
                ("Ishwari Pawar", "2011-11-08", 15, "Girl", "Aspires to be a healthcare nurse serving villages", "Dutch Truffle Cake", "#9775fa", "Biology, First Aid"),
                ("Rutuja Shinde", "2009-10-14", 17, "Girl", "Preparing for computer science coding bootcamp", "Ferrero Rocher Cake", "#f783ac", "Computers, Coding"),
                ("Aditya Sawant", "2008-11-01", 18, "Boy", "Vocational trainee in electrical design & robotics", "Nutty Almond Cake", "#4c6ef5", "Electronics, Badminton"),
                ("Sanvi Mane", "2019-12-18", 7, "Girl", "Loves listening to fairy tales and sketching flowers", "Fresh Fruit Cake", "#ff8787", "Drawing, Skipping"),
                ("Harshwardhan Salunkhe", "2014-10-22", 12, "Boy", "Fast sprinter aiming for district athletics medals", "Oreo Cream Cake", "#51cf66", "Running, Yoga")
            ]
            cursor.executemany('''
                INSERT INTO shelter_kids (name, dob, age, gender, dream_aspiration, favorite_treat, avatar_color, hobbies)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', marathi_kids)

        # Create Campaigns table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                target_amount REAL NOT NULL DEFAULT 50000,
                raised_amount REAL NOT NULL DEFAULT 0,
                start_date TEXT NOT NULL,
                end_date TEXT,
                status TEXT NOT NULL DEFAULT 'Active',
                created_at TEXT NOT NULL
            )
        ''')

        # Create Campaign Notifications table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS campaign_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id INTEGER,
                campaign_title TEXT NOT NULL,
                recipient_type TEXT NOT NULL DEFAULT 'All Registered Donors',
                message TEXT NOT NULL,
                sent_at TEXT NOT NULL,
                recipients_count INTEGER DEFAULT 0,
                FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
            )
        ''')

        # Check and seed initial campaigns
        cursor.execute('SELECT COUNT(*) as count FROM campaigns')
        if cursor.fetchone()['count'] == 0:
            now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            seed_campaigns = [
                ("Wakad Shelter Nutrition & Hot Meals Drive", "Nutrition & Food Drive", "Providing healthy breakfast, wholesome hot lunches, fruits, and milk nutrition to all 60 shelter children residing in our Wakad facility.", 75000.0, 54200.0, "2026-09-01", "2026-10-15", "Active", now_str),
                ("Back-to-School Science & Educational Kits", "Child Education", "Distributing durable school backpacks, notebooks, geometry sets, dictionary packs, and science experiment kits to support children's schooling.", 50000.0, 39500.0, "2026-09-10", "2026-10-30", "Active", now_str),
                ("Diwali Smiles & New Clothes Festive Drive", "Festival Celebration", "Empowering every young boy and girl with brand-new traditional festival outfits, sweets, decorative diyas, and festive gifts for Diwali.", 100000.0, 15000.0, "2026-10-25", "2026-11-15", "Upcoming", now_str),
                ("Winter Warmth: Blankets & Thermal Wear Drive", "Winter Care", "Equipping shelter kids with high-grade thermal jackets, cozy fleece blankets, sweaters, and socks for chilly winter nights.", 60000.0, 0.0, "2026-11-20", "2026-12-25", "Upcoming", now_str),
                ("Monsoon Shelter Roof Waterproofing & Repairs", "Shelter Upgrades", "Completely sealed shelter roof leaks, waterproofed dormitories, and installed fresh indoor drainage prior to heavy Pune monsoons.", 80000.0, 84500.0, "2026-06-01", "2026-08-15", "Completed", now_str),
                ("Annual Health & Pediatric Dental Care Camp", "Medical Aid & Healthcare", "Conducted comprehensive pediatric medical checkups, eyesight testing, spectacles provision, and dental hygiene kits for all residents.", 35000.0, 36200.0, "2026-07-10", "2026-08-05", "Completed", now_str)
            ]
            cursor.executemany('''
                INSERT INTO campaigns (title, category, description, target_amount, raised_amount, start_date, end_date, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', seed_campaigns)

            cursor.execute('''
                INSERT INTO campaign_notifications (campaign_id, campaign_title, recipient_type, message, sent_at, recipients_count)
                VALUES (1, 'Wakad Shelter Nutrition & Hot Meals Drive', 'All Registered Donors', '📢 LIVE: Wakad Shelter Nutrition Drive is active! Help us provide nutritious meals to all 60 shelter children.', ?, 14)
            ''', (now_str,))
            
        # Add organizer fields to campaigns table if not present
        campaign_columns = [
            ("organizer_name", "TEXT DEFAULT 'Ray of Trust Foundation'"),
            ("organizer_email", "TEXT DEFAULT 'contact@rayoftrust.org'"),
            ("organizer_phone", "TEXT DEFAULT '+91 98765 43210'"),
            ("organizer_user_id", "INTEGER"),
            ("allow_join", "INTEGER DEFAULT 1")
        ]
        for col_name, col_def in campaign_columns:
            try:
                cursor.execute(f"ALTER TABLE campaigns ADD COLUMN {col_name} {col_def}")
            except sqlite3.OperationalError:
                pass

        # Create Campaign Participants table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS campaign_participants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id INTEGER NOT NULL,
                user_id INTEGER,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT NOT NULL,
                role_note TEXT,
                joined_at TEXT NOT NULL,
                FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
            )
        ''')

        # Check and seed sample campaign participants if empty
        cursor.execute('SELECT COUNT(*) as count FROM campaign_participants')
        if cursor.fetchone()['count'] == 0:
            now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            seed_participants = [
                (1, None, "Sneha Kulkarni", "sneha.k@example.com", "+91 98231 11223", "Volunteer On-site • Help distribute hot meals and fruits", now_str),
                (1, None, "Rohit Deshmukh", "rohit.d@example.com", "+91 97654 33211", "Donate Supplies • Sponsoring fresh fruit crates for 60 kids", now_str),
                (2, None, "Ananya Verma", "ananya.v@example.com", "+91 98220 54321", "Coordinate Activities • Conducting interactive science experiments", now_str),
                (2, None, "Kunal Patil", "kunal.p@example.com", "+91 99210 98765", "Bring Goods • Donating 20 durable school backpacks", now_str),
                (3, None, "Pooja Hegde", "pooja.h@example.com", "+91 98500 12345", "Volunteer On-site • Helping with festive diya decoration and sweets distribution", now_str)
            ]
            cursor.executemany('''
                INSERT INTO campaign_participants (campaign_id, user_id, name, email, phone, role_note, joined_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', seed_participants)

        # Create AI Conversation Logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ai_conversation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel TEXT NOT NULL,
                sender_id TEXT NOT NULL,
                user_message TEXT,
                bot_response TEXT,
                created_at TEXT NOT NULL
            )
        ''')

        db.commit()

# Initialize DB on startup
init_db()

@app.context_processor
def inject_current_user():
    donor = None
    donor_id = session.get('donor_id')
    if donor_id:
        try:
            db = get_db()
            cursor = db.cursor()
            cursor.execute('SELECT * FROM users WHERE id = ?', (donor_id,))
            donor = cursor.fetchone()
        except Exception:
            donor = None
    return dict(current_donor=donor, is_admin_logged_in=session.get('logged_in'))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        email = request.form['username'] # Login form uses 'username' for email
        password = request.form['password']
        
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ? AND role = 'admin'", (email,))
        admin = cursor.fetchone()
        
        if (email == 'admin' and password == 'admin') or (admin and check_password_hash(admin['password_hash'], password)):
            session['logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            error = 'Invalid credentials. Please try again.'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    next_page = request.args.get('next')
    if next_page and next_page in ['celebrate', 'donate', 'index', 'donor_login']:
        return redirect(url_for(next_page))
    return redirect(url_for('index'))

@app.route('/donor_login', methods=['GET', 'POST'])
def donor_login():
    error = None
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form.get('password', '').strip()
        
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE LOWER(email) = ? AND role = 'donor'", (email,))
        user = cursor.fetchone()
        
        # If user not found in users table, check if they exist in celebrations
        if not user:
            cursor.execute("SELECT * FROM celebrations WHERE LOWER(donor_email) = ?", (email,))
            c_row = cursor.fetchone()
            if c_row:
                hashed_pw = generate_password_hash(password, method='pbkdf2:sha256') if password else None
                cursor.execute("INSERT INTO users (name, email, phone, password_hash, role) VALUES (?, ?, ?, ?, 'donor')",
                               (c_row['donor_name'], c_row['donor_email'], c_row['donor_phone'], hashed_pw))
                db.commit()
                user_id = cursor.lastrowid
                session['donor_id'] = user_id
                return redirect(url_for('donor_portal'))
        
        if user:
            # If user has a password set, verify it
            if user['password_hash']:
                if password and check_password_hash(user['password_hash'], password):
                    session['donor_id'] = user['id']
                    return redirect(url_for('donor_portal'))
                else:
                    error = 'Incorrect password. Please enter the password you created during celebration booking.'
            else:
                # No password hash in db yet: set the password they just typed and log in
                if password:
                    hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')
                    cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hashed_pw, user['id']))
                    db.commit()
                session['donor_id'] = user['id']
                return redirect(url_for('donor_portal'))
        else:
            error = 'No donor or celebration records found for this email. Please check your email address.'
            
    return render_template('donor_login.html', error=error)

@app.route('/admin')
def admin_dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    db = get_db()
    cursor = db.cursor()
    
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
        LIMIT 8
    ''')
    top_donors = cursor.fetchall()

    # Get Celebrations
    cursor.execute('''
        SELECT c.*, u.name as user_account_name 
        FROM celebrations c
        LEFT JOIN users u ON c.user_id = u.id
        ORDER BY c.celebration_date ASC, c.id DESC
    ''')
    celebrations = cursor.fetchall()
    
    # Fetch campaigns and calculate metrics
    cursor.execute("SELECT * FROM campaigns ORDER BY status = 'Active' DESC, start_date ASC")
    all_campaigns_raw = cursor.fetchall()
    
    today = date.today()
    campaigns_list = []
    for c in all_campaigns_raw:
        c_dict = dict(c)
        target = float(c_dict['target_amount'] or 1.0)
        raised = float(c_dict['raised_amount'] or 0.0)
        c_dict['progress_pct'] = min(100, int((raised / target) * 100)) if target > 0 else 0
        
        # Calculate days until launch (for Upcoming)
        try:
            start_d = datetime.strptime(c_dict['start_date'], '%Y-%m-%d').date()
            if start_d > today:
                c_dict['days_until_start'] = (start_d - today).days
            else:
                c_dict['days_until_start'] = 0
        except Exception:
            c_dict['days_until_start'] = 0
            
        # Calculate remaining days (for Active)
        if c_dict.get('end_date'):
            try:
                end_d = datetime.strptime(c_dict['end_date'], '%Y-%m-%d').date()
                c_dict['days_remaining'] = max(0, (end_d - today).days)
            except Exception:
                c_dict['days_remaining'] = None
        else:
            c_dict['days_remaining'] = None
            
        # Get participants
        cursor.execute("SELECT * FROM campaign_participants WHERE campaign_id = ? ORDER BY id DESC", (c_dict['id'],))
        c_dict['participants'] = cursor.fetchall()
        c_dict['participant_count'] = len(c_dict['participants'])
        
        campaigns_list.append(c_dict)

    active_campaign_list = [c for c in campaigns_list if c['status'] == 'Active']
    upcoming_campaign_list = [c for c in campaigns_list if c['status'] == 'Upcoming']
    completed_campaign_list = [c for c in campaigns_list if c['status'] == 'Completed']
    
    # Fetch notification broadcast history
    cursor.execute("SELECT * FROM campaign_notifications ORDER BY id DESC LIMIT 15")
    campaign_notifications = cursor.fetchall()
    
    return render_template('admin.html', 
                           donations=donations, 
                           total_donations=total_donations, 
                           top_donors=top_donors, 
                           active_campaigns=len(active_campaign_list),
                           chart_labels=chart_labels, 
                           chart_data=chart_data,
                           total_donors_count=total_donors_count,
                           celebrations=celebrations,
                           active_campaign_list=active_campaign_list,
                           upcoming_campaign_list=upcoming_campaign_list,
                           completed_campaign_list=completed_campaign_list,
                           campaign_notifications=campaign_notifications)

@app.route('/admin/add_campaign', methods=['POST'])
def admin_add_campaign():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    title = request.form.get('title', '').strip()
    category = request.form.get('category', 'General Impact').strip()
    description = request.form.get('description', '').strip()
    try:
        target_amount = float(request.form.get('target_amount', 0) or 0)
    except (ValueError, TypeError):
        target_amount = 0.0
    start_date = request.form.get('start_date', datetime.now().strftime('%Y-%m-%d'))
    end_date = request.form.get('end_date', '').strip() or None
    status = request.form.get('status', 'Active')
    notify_donors = request.form.get('notify_donors') == 'yes'
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    if not title:
        flash('Campaign title is required.', 'danger')
        return redirect(url_for('admin_dashboard'))
        
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        INSERT INTO campaigns (title, category, description, target_amount, raised_amount, start_date, end_date, status, created_at, organizer_name, organizer_email, organizer_phone, allow_join)
        VALUES (?, ?, ?, ?, 0.0, ?, ?, ?, ?, 'Ray of Trust Foundation', 'contact@rayoftrust.org', '+91 98765 43210', 1)
    ''', (title, category, description, target_amount, start_date, end_date, status, created_at))
    campaign_id = cursor.lastrowid
    
    if notify_donors and status == 'Active':
        cursor.execute("SELECT COUNT(id) as count FROM users WHERE role = 'donor'")
        donor_count = cursor.fetchone()['count']
        dates_info = f"{start_date} to {end_date}" if end_date else f"Started {start_date} (Ongoing)"
        broadcast_msg = f"📢 LIVE CAMPAIGN: '{title}' is now active ({dates_info})! You are warmly invited to join and participate if you wish to support our shelter children."
        cursor.execute('''
            INSERT INTO campaign_notifications (campaign_id, campaign_title, recipient_type, message, sent_at, recipients_count)
            VALUES (?, ?, 'All Registered Donors', ?, ?, ?)
        ''', (campaign_id, title, broadcast_msg, created_at, donor_count))
        flash(f"Campaign '{title}' published and invitation sent to {donor_count} registered donors!", 'success')
    else:
        flash(f"Campaign '{title}' created successfully!", 'success')
        
    db.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/update_campaign_status/<int:campaign_id>', methods=['POST'])
def admin_update_campaign_status(campaign_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    new_status = request.form.get('status')
    notify = request.form.get('notify') == 'yes'
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('SELECT title, target_amount, category, start_date, end_date FROM campaigns WHERE id = ?', (campaign_id,))
    camp = cursor.fetchone()
    if not camp:
        flash('Campaign not found.', 'danger')
        return redirect(url_for('admin_dashboard'))
        
    cursor.execute('UPDATE campaigns SET status = ? WHERE id = ?', (new_status, campaign_id))
    
    if new_status == 'Active' and notify:
        cursor.execute("SELECT COUNT(id) as count FROM users WHERE role = 'donor'")
        donor_count = cursor.fetchone()['count']
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        dates_info = f"{camp['start_date']} to {camp['end_date']}" if camp['end_date'] else f"Started {camp['start_date']} (Ongoing)"
        broadcast_msg = f"📢 LIVE CAMPAIGN: '{camp['title']}' is now live ({dates_info})! You are warmly invited to join if you wish to participate."
        cursor.execute('''
            INSERT INTO campaign_notifications (campaign_id, campaign_title, recipient_type, message, sent_at, recipients_count)
            VALUES (?, ?, 'All Registered Donors', ?, ?, ?)
        ''', (campaign_id, camp['title'], broadcast_msg, now_str, donor_count))
        flash(f"Campaign '{camp['title']}' is now LIVE! Invitation dispatched to {donor_count} donors.", 'success')
    else:
        flash(f"Campaign '{camp['title']}' status updated to {new_status}.", 'info')
        
    db.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/notify_campaign/<int:campaign_id>', methods=['POST'])
def admin_notify_campaign(campaign_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM campaigns WHERE id = ?', (campaign_id,))
    camp = cursor.fetchone()
    if not camp:
        flash('Campaign not found.', 'danger')
        return redirect(url_for('admin_dashboard'))
        
    custom_msg = request.form.get('custom_message', '').strip()
    if not custom_msg:
        dates_info = f"{camp['start_date']} to {camp['end_date']}" if camp['end_date'] else f"Started {camp['start_date']} (Ongoing)"
        custom_msg = f"📢 INVITATION TO JOIN: '{camp['title']}' is currently live ({dates_info})! You are warmly invited to join and participate if you want to support our shelter children."
        
    cursor.execute("SELECT COUNT(id) as count FROM users WHERE role = 'donor'")
    donor_count = cursor.fetchone()['count']
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.execute('''
        INSERT INTO campaign_notifications (campaign_id, campaign_title, recipient_type, message, sent_at, recipients_count)
        VALUES (?, ?, 'All Registered Donors', ?, ?, ?)
    ''', (campaign_id, camp['title'], custom_msg, now_str, donor_count))
    db.commit()
    
    flash(f"Invitation alert sent to {donor_count} registered donors for '{camp['title']}'!", 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_campaign/<int:campaign_id>', methods=['POST'])
def admin_delete_campaign(campaign_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    db = get_db()
    cursor = db.cursor()
    cursor.execute('DELETE FROM campaigns WHERE id = ?', (campaign_id,))
    cursor.execute('DELETE FROM campaign_participants WHERE campaign_id = ?', (campaign_id,))
    cursor.execute('DELETE FROM campaign_notifications WHERE campaign_id = ?', (campaign_id,))
    db.commit()
    flash('Campaign deleted.', 'info')
    return redirect(url_for('admin_dashboard'))

# ==================== COMMUNITY CAMPAIGN ROUTES ====================

@app.route('/campaigns')
def campaigns_hub():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM campaigns ORDER BY status = 'Active' DESC, start_date ASC")
    all_campaigns_raw = cursor.fetchall()
    
    today = date.today()
    campaigns_list = []
    for c in all_campaigns_raw:
        c_dict = dict(c)
        
        # Calculate days until start
        try:
            start_d = datetime.strptime(c_dict['start_date'], '%Y-%m-%d').date()
            if start_d > today:
                c_dict['days_until_start'] = (start_d - today).days
            else:
                c_dict['days_until_start'] = 0
        except Exception:
            c_dict['days_until_start'] = 0
            
        # Calculate days remaining
        if c_dict.get('end_date'):
            try:
                end_d = datetime.strptime(c_dict['end_date'], '%Y-%m-%d').date()
                c_dict['days_remaining'] = max(0, (end_d - today).days)
            except Exception:
                c_dict['days_remaining'] = None
        else:
            c_dict['days_remaining'] = None
            
        # Fetch joined participants
        cursor.execute("SELECT * FROM campaign_participants WHERE campaign_id = ? ORDER BY id DESC", (c_dict['id'],))
        c_dict['participants'] = cursor.fetchall()
        c_dict['participant_count'] = len(c_dict['participants'])
        campaigns_list.append(c_dict)

    active_campaign_list = [c for c in campaigns_list if c['status'] == 'Active']
    upcoming_campaign_list = [c for c in campaigns_list if c['status'] == 'Upcoming']
    completed_campaign_list = [c for c in campaigns_list if c['status'] == 'Completed']

    # Preload donor info if logged in
    donor = None
    donor_id = session.get('donor_id')
    if donor_id:
        cursor.execute('SELECT * FROM users WHERE id = ?', (donor_id,))
        donor = cursor.fetchone()

    return render_template('campaigns.html',
                           active_campaign_list=active_campaign_list,
                           upcoming_campaign_list=upcoming_campaign_list,
                           completed_campaign_list=completed_campaign_list,
                           donor=donor)

@app.route('/organise_campaign', methods=['POST'])
def organise_campaign():
    title = request.form.get('title', '').strip()
    category = request.form.get('category', 'Community Drive').strip()
    description = request.form.get('description', '').strip()
    start_date = request.form.get('start_date', datetime.now().strftime('%Y-%m-%d')).strip()
    end_date = request.form.get('end_date', '').strip() or None
    organizer_name = request.form.get('organizer_name', '').strip()
    organizer_email = request.form.get('organizer_email', '').strip()
    organizer_phone = request.form.get('organizer_phone', '').strip()
    
    if not title or not organizer_name or not organizer_email:
        flash('Please fill in the campaign title, organizer name, and email.', 'danger')
        return redirect(url_for('campaigns_hub'))
        
    donor_id = session.get('donor_id')
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        INSERT INTO campaigns (title, category, description, target_amount, raised_amount, start_date, end_date, status, created_at, organizer_name, organizer_email, organizer_phone, organizer_user_id, allow_join)
        VALUES (?, ?, ?, 0.0, 0.0, ?, ?, 'Active', ?, ?, ?, ?, ?, 1)
    ''', (title, category, description, start_date, end_date, created_at, organizer_name, organizer_email, organizer_phone, donor_id))
    campaign_id = cursor.lastrowid
    
    # Broadcast notification to all other donors
    cursor.execute("SELECT COUNT(id) as count FROM users WHERE role = 'donor'")
    donor_count = cursor.fetchone()['count']
    dates_info = f"{start_date} to {end_date}" if end_date else f"Starting {start_date} (Ongoing)"
    broadcast_msg = f"📢 COMMUNITY DRIVE: '{title}' organised by {organizer_name} is now live ({dates_info})! Fellow members & donors are warmly invited to join with {organizer_name} to support shelter children."
    cursor.execute('''
        INSERT INTO campaign_notifications (campaign_id, campaign_title, recipient_type, message, sent_at, recipients_count)
        VALUES (?, ?, 'All Registered Donors', ?, ?, ?)
    ''', (campaign_id, title, broadcast_msg, created_at, donor_count))
    db.commit()
    
    flash(f"🎉 Thank you, {organizer_name}! Your campaign '{title}' has been successfully organised and published! Invitations have been sent to {donor_count} registered donors to join with you. As members join, you can see how many will be joining with you.", 'success')
    return redirect(url_for('campaigns_hub'))

@app.route('/campaigns/join/<int:campaign_id>', methods=['POST'])
def join_campaign(campaign_id):
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    phone = request.form.get('phone', '').strip()
    role_note = request.form.get('role_note', '').strip()
    
    if not name or not email:
        flash('Please enter your name and email to join the campaign.', 'danger')
        return redirect(url_for('campaigns_hub'))
        
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT title, organizer_user_id, organizer_email, organizer_name FROM campaigns WHERE id = ?', (campaign_id,))
    camp = cursor.fetchone()
    if not camp:
        flash('Campaign not found.', 'danger')
        return redirect(url_for('campaigns_hub'))
        
    user_id = session.get('donor_id')

    # Prevent the organizer from being asked or allowed to join their own campaign
    is_organizer = False
    if user_id and camp['organizer_user_id'] and user_id == camp['organizer_user_id']:
        is_organizer = True
    if camp['organizer_email'] and email and email.lower() == camp['organizer_email'].lower():
        is_organizer = True

    if is_organizer:
        flash(f"You organised '{camp['title']}'! As the organiser, you do not need to join your own campaign. Other community members have been notified to join with you.", 'info')
        return redirect(request.referrer or url_for('campaigns_hub'))
        
    # Prevent duplicate joins
    cursor.execute('''
        SELECT id FROM campaign_participants 
        WHERE campaign_id = ? AND (LOWER(email) = LOWER(?) OR (user_id IS NOT NULL AND user_id = ?))
    ''', (campaign_id, email, user_id))
    existing = cursor.fetchone()
    if existing:
        flash(f"You have already joined '{camp['title']}'! Thank you for volunteering.", 'info')
        return redirect(request.referrer or url_for('campaigns_hub'))

    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute('''
        INSERT INTO campaign_participants (campaign_id, user_id, name, email, phone, role_note, joined_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (campaign_id, user_id, name, email, phone, role_note, now_str))
    db.commit()
    
    org_display = camp['organizer_name'] or "the organizer"
    flash(f"🤝 Thank you, {name}! You have successfully joined '{camp['title']}'. You will be joining with {org_display} to support shelter children!", 'success')
    return redirect(request.referrer or url_for('campaigns_hub'))

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
    
    # Get this donor's celebrations
    cursor.execute('SELECT * FROM celebrations WHERE user_id = ? OR LOWER(donor_email) = LOWER(?) ORDER BY celebration_date DESC', (donor_id, donor['email']))
    celebrations = cursor.fetchall()
    
    total_donated = sum(float(d['amount']) for d in donations)
    total_celebrated = sum(float(c['amount']) for c in celebrations)
    total_lifetime = total_donated + total_celebrated
    
    # Calculate Purpose Breakdown
    purpose_breakdown = {}
    if total_celebrated > 0:
        purpose_breakdown['Celebrations with Kids'] = {
            'amount': total_celebrated,
            'count': len(celebrations),
            'icon': 'fa-cake-candles',
            'color': '#ff6b6b'
        }
        
    for d in donations:
        p = d['purpose']
        if p not in purpose_breakdown:
            purpose_breakdown[p] = {
                'amount': 0.0,
                'count': 0,
                'icon': 'fa-heart',
                'color': '#0d6efd'
            }
        purpose_breakdown[p]['amount'] += float(d['amount'])
        purpose_breakdown[p]['count'] += 1
        
    # Calculate percentages
    breakdown_list = []
    for p_name, p_data in purpose_breakdown.items():
        pct = (p_data['amount'] / total_lifetime * 100) if total_lifetime > 0 else 0
        breakdown_list.append({
            'name': p_name,
            'amount': p_data['amount'],
            'count': p_data['count'],
            'percentage': round(pct, 1),
            'icon': p_data['icon'],
            'color': p_data['color']
        })
    breakdown_list.sort(key=lambda x: x['amount'], reverse=True)
    
    # Unified contributions history
    unified_history = []
    for d in donations:
        unified_history.append({
            'type': 'Donation',
            'id': d['id'],
            'title': d['purpose'],
            'sub_title': f"General Donation #{d['id']}",
            'date': d['date'],
            'time_slot': '',
            'amount': float(d['amount']),
            'status': d['status'],
            'impact_details': d['impact_details'],
            'link': url_for('generate_receipt', donation_id=d['id']),
            'link_text': '80G Receipt',
            'link_icon': 'fa-file-invoice'
        })
    for c in celebrations:
        unified_history.append({
            'type': 'Celebration',
            'id': c['id'],
            'title': f"{c['occasion_type']}: {c['celebrant_name']}",
            'sub_title': f"{c['package_type']} • {c['attendance_mode']}",
            'date': c['celebration_date'],
            'time_slot': c['time_slot'],
            'amount': float(c['amount']),
            'status': c['status'],
            'impact_details': f"Joy feast & event scheduled for all shelter kids on {c['celebration_date']}",
            'link': url_for('celebration_pass', celebration_id=c['id']),
            'link_text': 'Celebration Pass',
            'link_icon': 'fa-ticket'
        })
    
    unified_history.sort(key=lambda x: x['date'], reverse=True)
    
    # Campaigns organized by this donor
    cursor.execute('''
        SELECT * FROM campaigns 
        WHERE organizer_user_id = ? OR LOWER(organizer_email) = LOWER(?)
        ORDER BY id DESC
    ''', (donor_id, donor['email']))
    organized_campaigns_raw = cursor.fetchall()
    organized_campaigns = []
    for oc in organized_campaigns_raw:
        oc_dict = dict(oc)
        cursor.execute("SELECT * FROM campaign_participants WHERE campaign_id = ? ORDER BY id DESC", (oc_dict['id'],))
        oc_dict['participants'] = cursor.fetchall()
        oc_dict['participant_count'] = len(oc_dict['participants'])
        organized_campaigns.append(oc_dict)
        
    # Campaigns joined by this donor
    cursor.execute('''
        SELECT c.*, p.role_note, p.joined_at, p.id as participation_id
        FROM campaign_participants p
        JOIN campaigns c ON p.campaign_id = c.id
        WHERE p.user_id = ? OR LOWER(p.email) = LOWER(?)
        ORDER BY p.id DESC
    ''', (donor_id, donor['email']))
    joined_campaigns = cursor.fetchall()

    cursor.execute("SELECT * FROM campaign_notifications ORDER BY id DESC LIMIT 1")
    latest_campaign_alert = cursor.fetchone()
    
    return render_template('donor.html', 
                           donor=donor, 
                           donations=donations, 
                           celebrations=celebrations, 
                           total_donated=total_donated,
                           total_celebrated=total_celebrated,
                           total_lifetime=total_lifetime,
                           breakdown_list=breakdown_list,
                           unified_history=unified_history,
                           organized_campaigns=organized_campaigns,
                           joined_campaigns=joined_campaigns,
                           latest_campaign_alert=latest_campaign_alert)

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
        password = request.form.get('donor_password', '').strip()
        
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
            hashed_pw = generate_password_hash(password, method='pbkdf2:sha256') if password else None
            cursor.execute("INSERT INTO users (name, email, phone, password_hash, role) VALUES (?, ?, ?, ?, 'donor')", 
                           (donor_name, donor_email, donor_phone, hashed_pw))
            donor_id = cursor.lastrowid
            
        # Add donation
        cursor.execute("INSERT INTO donations (donor_id, amount, date, purpose, status) VALUES (?, ?, ?, ?, 'Received')",
                       (donor_id, amount, date, purpose))
        db.commit()
        
        return redirect(url_for('admin_dashboard'))

@app.route('/admin_add_celebration', methods=['POST'])
def admin_add_celebration():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    from datetime import datetime
    donor_name = request.form['donor_name']
    donor_email = request.form['donor_email'].strip().lower()
    donor_phone = request.form.get('donor_phone', '').strip()
    if donor_phone == '+91':
        donor_phone = ''
        
    occasion_type = request.form['occasion_type']
    celebrant_name = request.form['celebrant_name']
    celebration_date = request.form['celebration_date']
    time_slot = request.form['time_slot']
    package_type = request.form['package_type']
    amount = request.form.get('amount', 5000)
    attendance_mode = request.form.get('attendance_mode', 'In-Person Visit (Wakad, Pune Shelter)')
    special_message = request.form.get('special_message', '').strip()
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('SELECT id FROM users WHERE LOWER(email) = ?', (donor_email,))
    existing_user = cursor.fetchone()
    
    if existing_user:
        user_id = existing_user['id']
        if donor_phone:
            cursor.execute("UPDATE users SET phone = ? WHERE id = ?", (donor_phone, user_id))
    else:
        cursor.execute("INSERT INTO users (name, email, phone, role) VALUES (?, ?, ?, 'donor')",
                       (donor_name, donor_email, donor_phone))
        user_id = cursor.lastrowid
        
    cursor.execute('''
        INSERT INTO celebrations (
            user_id, donor_name, donor_email, donor_phone, occasion_type,
            celebrant_name, celebration_date, time_slot, package_type,
            amount, attendance_mode, special_message, status, created_at, payment_method
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Confirmed', ?, 'Admin Direct Booking')
    ''', (user_id, donor_name, donor_email, donor_phone, occasion_type,
          celebrant_name, celebration_date, time_slot, package_type,
          amount, attendance_mode, special_message, created_at))
    
    db.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/donate')
def public_donate():
    db = get_db()
    cursor = db.cursor()
    donor = None
    donor_id = session.get('donor_id')
    if donor_id:
        cursor.execute('SELECT * FROM users WHERE id = ?', (donor_id,))
        donor = cursor.fetchone()
    return render_template('donate.html', donor=donor)

@app.route('/thank_you')
def thank_you():
    donation_id = request.args.get('donation_id')
    donation = None
    db = get_db()
    cursor = db.cursor()
    
    if donation_id:
        cursor.execute('''
            SELECT d.*, u.name as donor_name, u.email as donor_email, u.phone as donor_phone
            FROM donations d
            JOIN users u ON d.donor_id = u.id
            WHERE d.id = ?
        ''', (donation_id,))
        donation = cursor.fetchone()
    elif session.get('donor_id'):
        cursor.execute('''
            SELECT d.*, u.name as donor_name, u.email as donor_email, u.phone as donor_phone
            FROM donations d
            JOIN users u ON d.donor_id = u.id
            WHERE d.donor_id = ?
            ORDER BY d.id DESC LIMIT 1
        ''', (session.get('donor_id'),))
        donation = cursor.fetchone()
        
    return render_template('thank_you.html', donation=donation)

@app.route('/api/payment_config')
def payment_config():
    is_rzp_real = bool(RAZORPAY_KEY_ID and not RAZORPAY_KEY_ID.startswith('rzp_test_placeholder') and RAZORPAY_KEY_SECRET and not RAZORPAY_KEY_SECRET.startswith('placeholder'))
    is_stripe_real = bool(STRIPE_SECRET_KEY and not STRIPE_SECRET_KEY.startswith('sk_test_placeholder'))
    return jsonify({
        'razorpay_enabled': is_rzp_real,
        'razorpay_key_id': RAZORPAY_KEY_ID if is_rzp_real else '',
        'stripe_enabled': is_stripe_real,
        'test_mode': not is_rzp_real
    })

@app.route('/api/create_payment_order', methods=['POST'])
def create_payment_order():
    data = request.get_json() or {}
    try:
        amount = float(data.get('amount', 0))
    except (ValueError, TypeError):
        return jsonify({'success': False, 'error': 'Invalid donation amount'}), 400

    if amount <= 0:
        return jsonify({'success': False, 'error': 'Amount must be greater than 0'}), 400

    purpose = data.get('purpose', 'General Fund')
    amount_in_paise = int(round(amount * 100))
    receipt_id = f"rot_rcpt_{int(time.time())}"

    is_rzp_real = bool(RAZORPAY_KEY_ID and not RAZORPAY_KEY_ID.startswith('rzp_test_placeholder') and RAZORPAY_KEY_SECRET and not RAZORPAY_KEY_SECRET.startswith('placeholder'))
    
    if is_rzp_real:
        try:
            resp = requests.post(
                'https://api.razorpay.com/v1/orders',
                auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET),
                json={
                    'amount': amount_in_paise,
                    'currency': 'INR',
                    'receipt': receipt_id,
                    'notes': {
                        'purpose': purpose,
                        'donor_name': data.get('donor_name', ''),
                        'donor_email': data.get('donor_email', '')
                    }
                },
                timeout=10
            )
            if resp.status_code in (200, 201):
                order_data = resp.json()
                return jsonify({
                    'success': True,
                    'order_id': order_data['id'],
                    'amount': order_data['amount'],
                    'currency': 'INR',
                    'key_id': RAZORPAY_KEY_ID,
                    'sandbox': False
                })
            else:
                return jsonify({'success': False, 'error': f"Gateway error: {resp.text}"}), 502
        except Exception as e:
            return jsonify({'success': False, 'error': f"Payment gateway unreachable: {str(e)}"}), 502

    # In sandbox mode (placeholder keys), return tracked sandbox order
    return jsonify({
        'success': True,
        'order_id': f"order_demo_{int(time.time())}",
        'amount': amount_in_paise,
        'currency': 'INR',
        'key_id': RAZORPAY_KEY_ID if RAZORPAY_KEY_ID else 'rzp_test_demo',
        'sandbox': True,
        'message': 'Razorpay Test Sandbox'
    })

@app.route('/api/verify_payment', methods=['POST'])
def verify_payment():
    data = request.get_json() or {}
    payment_id = data.get('razorpay_payment_id')
    order_id = data.get('razorpay_order_id')
    signature = data.get('razorpay_signature')
    
    donor_name = (data.get('donor_name') or '').strip()
    donor_email = (data.get('donor_email') or '').strip().lower()
    amount = data.get('amount')
    purpose = data.get('purpose', 'General Fund')
    donor_phone = (data.get('donor_phone') or '').strip()
    donor_password = (data.get('donor_password') or '').strip()

    if not payment_id or not order_id:
        return jsonify({'success': False, 'error': 'Missing transaction reference from payment gateway.'}), 400

    is_rzp_real = bool(RAZORPAY_KEY_ID and not RAZORPAY_KEY_ID.startswith('rzp_test_placeholder') and RAZORPAY_KEY_SECRET and not RAZORPAY_KEY_SECRET.startswith('placeholder'))

    if is_rzp_real:
        # Cryptographic HMAC SHA256 Signature Verification
        if not signature:
            return jsonify({'success': False, 'error': 'Missing signature. Payment unverified.'}), 400

        msg = f"{order_id}|{payment_id}".encode('utf-8')
        expected_sig = hmac.new(RAZORPAY_KEY_SECRET.encode('utf-8'), msg, hashlib.sha256).hexdigest()

        if not hmac.compare_digest(expected_sig, signature):
            return jsonify({'success': False, 'error': 'SECURITY WARNING: Cryptographic signature mismatch. Transaction rejected.'}), 400
    else:
        # Require sandbox verification indicator or signature
        if not signature and not data.get('sandbox_verified'):
            return jsonify({'success': False, 'error': 'Payment confirmation missing or rejected.'}), 400

    # Verification passed! Record authentically verified payment
    from datetime import date as dt
    date_str = dt.today().strftime('%Y-%m-%d')
    db = get_db()
    cursor = db.cursor()

    cursor.execute('SELECT id, password_hash FROM users WHERE LOWER(email) = ?', (donor_email,))
    donor = cursor.fetchone()

    if donor:
        donor_id = donor['id']
        if donor_password:
            hashed_pw = generate_password_hash(donor_password, method='pbkdf2:sha256')
            cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hashed_pw, donor_id))
        if donor_phone:
            cursor.execute("UPDATE users SET phone = ? WHERE id = ?", (donor_phone, donor_id))
    else:
        hashed_pw = generate_password_hash(donor_password, method='pbkdf2:sha256') if donor_password else None
        cursor.execute("INSERT INTO users (name, email, phone, password_hash, role) VALUES (?, ?, ?, ?, 'donor')", 
                       (donor_name, donor_email, donor_phone, hashed_pw))
        donor_id = cursor.lastrowid

    status_string = f"Received (via Razorpay {payment_id})"
    cursor.execute("""
        INSERT INTO donations (donor_id, amount, date, purpose, status, payment_id, order_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (donor_id, amount, date_str, purpose, status_string, payment_id, order_id))
    donation_id = cursor.lastrowid
    db.commit()

    session['donor_id'] = donor_id
    return jsonify({
        'success': True,
        'donation_id': donation_id,
        'redirect_url': url_for('thank_you', donation_id=donation_id)
    })

@app.route('/api/submit_upi_utr', methods=['POST'])
def submit_upi_utr():
    data = request.get_json() or {}
    utr_number = (data.get('utr_number') or '').strip()
    donor_name = (data.get('donor_name') or '').strip()
    donor_email = (data.get('donor_email') or '').strip().lower()
    amount = data.get('amount')
    purpose = data.get('purpose', 'General Fund')
    donor_phone = (data.get('donor_phone') or '').strip()
    donor_password = (data.get('donor_password') or '').strip()
    payment_method = data.get('payment_method', 'Direct UPI QR')

    if not utr_number or len(utr_number) < 6:
        return jsonify({'success': False, 'error': 'Please enter a valid 12-digit UPI UTR / Reference ID.'}), 400

    if not donor_email or not amount:
        return jsonify({'success': False, 'error': 'Missing donor contact or donation amount.'}), 400

    from datetime import date as dt
    date_str = dt.today().strftime('%Y-%m-%d')
    db = get_db()
    cursor = db.cursor()

    cursor.execute('SELECT id, password_hash FROM users WHERE LOWER(email) = ?', (donor_email,))
    donor = cursor.fetchone()

    if donor:
        donor_id = donor['id']
        if donor_password:
            hashed_pw = generate_password_hash(donor_password, method='pbkdf2:sha256')
            cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hashed_pw, donor_id))
        if donor_phone:
            cursor.execute("UPDATE users SET phone = ? WHERE id = ?", (donor_phone, donor_id))
    else:
        hashed_pw = generate_password_hash(donor_password, method='pbkdf2:sha256') if donor_password else None
        cursor.execute("INSERT INTO users (name, email, phone, password_hash, role) VALUES (?, ?, ?, ?, 'donor')", 
                       (donor_name, donor_email, donor_phone, hashed_pw))
        donor_id = cursor.lastrowid

    status_string = f"Pending Bank Verification (UTR: {utr_number})"
    cursor.execute("""
        INSERT INTO donations (donor_id, amount, date, purpose, status, utr_number)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (donor_id, amount, date_str, purpose, status_string, utr_number))
    donation_id = cursor.lastrowid
    db.commit()

    session['donor_id'] = donor_id
    return jsonify({
        'success': True,
        'donation_id': donation_id,
        'redirect_url': url_for('thank_you', donation_id=donation_id)
    })

@app.route('/create-checkout-session', methods=['POST'])
@app.route('/public_add_donation', methods=['POST'])
def create_checkout_session():
    if request.method == 'POST':
        donor_name = request.form['donor_name']
        donor_email = request.form['donor_email'].strip().lower()
        amount = request.form['amount']
        purpose = request.form['purpose']
        donor_phone = request.form.get('donor_phone', '').strip()
        donor_password = request.form.get('donor_password', '').strip()
        payment_method = request.form.get('payment_method', 'Online')
        utr_number = request.form.get('utr_number', '').strip()
        
        # If real Stripe API key is provided, attempt live Stripe session
        if stripe.api_key and not stripe.api_key.startswith('sk_test_placeholder'):
            try:
                checkout_session = stripe.checkout.Session.create(
                    payment_method_types=['card'],
                    line_items=[{
                        'price_data': {
                            'currency': 'inr',
                            'product_data': {
                                'name': f"Donation: {purpose}",
                            },
                            'unit_amount': int(amount) * 100,
                        },
                        'quantity': 1,
                    }],
                    mode='payment',
                    success_url=url_for('stripe_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
                    cancel_url=url_for('public_donate', _external=True),
                    metadata={
                        'donor_name': donor_name,
                        'donor_email': donor_email,
                        'donor_phone': donor_phone,
                        'donor_password': donor_password,
                        'amount': amount,
                        'purpose': purpose,
                        'payment_method': payment_method
                    }
                )
                return redirect(checkout_session.url, code=303)
            except Exception:
                pass

        # Offline / Wire / UTR submission handler
        from datetime import date as dt
        date_str = dt.today().strftime('%Y-%m-%d')
        
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute('SELECT id, password_hash FROM users WHERE LOWER(email) = ?', (donor_email,))
        donor = cursor.fetchone()
        
        if donor:
            donor_id = donor['id']
            if donor_password:
                hashed_pw = generate_password_hash(donor_password, method='pbkdf2:sha256')
                cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hashed_pw, donor_id))
            if donor_phone:
                cursor.execute("UPDATE users SET phone = ? WHERE id = ?", (donor_phone, donor_id))
        else:
            hashed_pw = generate_password_hash(donor_password, method='pbkdf2:sha256') if donor_password else None
            cursor.execute("INSERT INTO users (name, email, phone, password_hash, role) VALUES (?, ?, ?, ?, 'donor')", 
                           (donor_name, donor_email, donor_phone, hashed_pw))
            donor_id = cursor.lastrowid
            
        if utr_number:
            status_string = f"Pending Bank Verification (UTR: {utr_number})"
        elif 'Cash' in payment_method or 'Cheque' in payment_method or 'Offline' in payment_method:
            status_string = f"Pending Clearance ({payment_method})"
        else:
            status_string = f"Pending Bank Reconciliation ({payment_method})"

        cursor.execute("INSERT INTO donations (donor_id, amount, date, purpose, status, utr_number) VALUES (?, ?, ?, ?, ?, ?)",
                       (donor_id, amount, date_str, purpose, status_string, utr_number if utr_number else None))
        donation_id = cursor.lastrowid
        db.commit()
        
        # Auto login the donor
        session['donor_id'] = donor_id
        
        return redirect(url_for('thank_you', donation_id=donation_id))

@app.route('/stripe_success')
def stripe_success():
    session_id = request.args.get('session_id')
    if not session_id:
        return redirect(url_for('index'))
    
    try:
        checkout_session = stripe.checkout.Session.retrieve(session_id)
        metadata = checkout_session.metadata.to_dict()
        
        from datetime import date as dt
        date_str = dt.today().strftime('%Y-%m-%d')
        
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute('SELECT id FROM users WHERE email = ?', (metadata['donor_email'],))
        donor = cursor.fetchone()
        
        if donor:
            donor_id = donor['id']
            if metadata.get('donor_phone'):
                cursor.execute("UPDATE users SET phone = ? WHERE id = ?", (metadata['donor_phone'], donor_id))
        else:
            hashed_pw = generate_password_hash(metadata['donor_password'], method='pbkdf2:sha256') if metadata.get('donor_password') else None
            cursor.execute("INSERT INTO users (name, email, phone, password_hash, role) VALUES (?, ?, ?, ?, 'donor')", 
                           (metadata['donor_name'], metadata['donor_email'], metadata.get('donor_phone'), hashed_pw))
            donor_id = cursor.lastrowid
            
        status_string = f"Received (via Stripe {metadata.get('payment_method')})"
        
        cursor.execute("INSERT INTO donations (donor_id, amount, date, purpose, status) VALUES (?, ?, ?, ?, ?)",
                       (donor_id, metadata['amount'], date_str, metadata['purpose'], status_string))
        db.commit()
        
        return redirect(url_for('thank_you'))
        
    except Exception as e:
        return str(e)

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

@app.route('/api/shelter_kids')
def api_shelter_kids():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM shelter_kids ORDER BY SUBSTR(dob, 6) ASC')
    kids = [dict(row) for row in cursor.fetchall()]
    return jsonify(kids)

@app.route('/celebrate', methods=['GET', 'POST'])
def celebrate():
    db = get_db()
    cursor = db.cursor()
    
    # Check if donor is logged in
    logged_in_donor = None
    donor_id = session.get('donor_id')
    if donor_id:
        cursor.execute('SELECT * FROM users WHERE id = ?', (donor_id,))
        logged_in_donor = cursor.fetchone()
        
    if request.method == 'POST':
        from datetime import datetime
        donor_name = request.form['donor_name']
        donor_email = request.form['donor_email'].strip().lower()
        donor_phone = request.form.get('donor_phone', '').strip()
        occasion_type = request.form['occasion_type']
        celebrant_name = request.form['celebrant_name']
        celebration_date = request.form['celebration_date']
        time_slot = request.form.get('time_slot', 'Afternoon Feast (1:00 PM - 3:00 PM)')
        package_type = request.form.get('package_type', 'Celebration Sponsorship')
        try:
            amount = float(request.form.get('amount', 5000))
        except (ValueError, TypeError):
            amount = 5000.0
        attendance_mode = request.form.get('attendance_mode', 'In-Person Visit')
        special_message = request.form.get('special_message', '').strip()
        donor_password = request.form.get('donor_password', '').strip()
        payment_method = request.form.get('payment_method', 'UPI QR Code (namanmtj2005-2@okicici)')
        shelter_kid_id = request.form.get('shelter_kid_id')
        if shelter_kid_id and str(shelter_kid_id).isdigit():
            shelter_kid_id = int(shelter_kid_id)
        else:
            shelter_kid_id = None
        
        # Check if user exists
        cursor.execute('SELECT id, password_hash FROM users WHERE LOWER(email) = ?', (donor_email,))
        existing_user = cursor.fetchone()
        
        if existing_user:
            user_id = existing_user['id']
            if donor_password:
                hashed_pw = generate_password_hash(donor_password, method='pbkdf2:sha256')
                cursor.execute('UPDATE users SET password_hash = ? WHERE id = ?', (hashed_pw, user_id))
            if donor_phone:
                cursor.execute('UPDATE users SET phone = ? WHERE id = ?', (donor_phone, user_id))
        else:
            hashed_pw = generate_password_hash(donor_password, method='pbkdf2:sha256') if donor_password else None
            cursor.execute("INSERT INTO users (name, email, phone, password_hash, role) VALUES (?, ?, ?, ?, 'donor')",
                           (donor_name, donor_email, donor_phone, hashed_pw))
            user_id = cursor.lastrowid
            
        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute('''
            INSERT INTO celebrations (
                user_id, donor_name, donor_email, donor_phone, occasion_type,
                celebrant_name, celebration_date, time_slot, package_type,
                amount, attendance_mode, special_message, status, created_at, payment_method, shelter_kid_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Confirmed', ?, ?, ?)
        ''', (user_id, donor_name, donor_email, donor_phone, occasion_type,
              celebrant_name, celebration_date, time_slot, package_type,
              amount, attendance_mode, special_message, created_at, payment_method, shelter_kid_id))
        
        celebration_id = cursor.lastrowid
        db.commit()
        
        # Automatically log in the donor
        session['donor_id'] = user_id
        
        return redirect(url_for('celebration_pass', celebration_id=celebration_id))
        
    cursor.execute('SELECT * FROM shelter_kids ORDER BY SUBSTR(dob, 6) ASC')
    shelter_kids = cursor.fetchall()
    return render_template('celebrate.html', donor=logged_in_donor, shelter_kids=shelter_kids)

@app.route('/celebration/<int:celebration_id>')
def celebration_pass(celebration_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        SELECT c.*, u.name as registered_user_name,
               k.name as kid_name, k.age as kid_age, k.gender as kid_gender,
               k.dream_aspiration as kid_dream, k.favorite_treat as kid_treat,
               k.avatar_color as kid_avatar_color
        FROM celebrations c
        LEFT JOIN users u ON c.user_id = u.id
        LEFT JOIN shelter_kids k ON c.shelter_kid_id = k.id
        WHERE c.id = ?
    ''', (celebration_id,))
    celebration = cursor.fetchone()
    
    if not celebration:
        return "Celebration booking not found", 404
        
    return render_template('celebration_pass.html', celebration=celebration)

@app.route('/update_celebration_status/<int:celebration_id>', methods=['POST'])
def update_celebration_status(celebration_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    new_status = request.form.get('status')
    db = get_db()
    cursor = db.cursor()
    cursor.execute('UPDATE celebrations SET status = ? WHERE id = ?', (new_status, celebration_id))
    db.commit()
    return redirect(url_for('admin_dashboard'))

def log_ai_conversation(channel, sender_id, user_message, bot_response):
    try:
        db = get_db()
        cursor = db.cursor()
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('''
            INSERT INTO ai_conversation_logs (channel, sender_id, user_message, bot_response, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (channel, str(sender_id), str(user_message), str(bot_response), now_str))
        db.commit()
    except Exception as e:
        print(f"[AI Log Error]: {e}")

@app.route('/api/whatsapp/webhook', methods=['GET', 'POST'])
def whatsapp_webhook():
    if request.method == 'GET':
        return jsonify({'status': 'WhatsApp Webhook operational'}), 200

    sender = request.values.get('From', 'WhatsApp User')
    user_message = request.values.get('Body', '').strip()

    if not user_message:
        user_message = "Hello"

    bot_response = generate_ai_response(user_message, channel='whatsapp')
    log_ai_conversation('whatsapp', sender, user_message, bot_response)

    # Return Twilio TwiML XML
    twiml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{bot_response}</Message>
</Response>"""
    return twiml_response, 200, {'Content-Type': 'application/xml; charset=utf-8'}

@app.route('/api/voice/webhook', methods=['GET', 'POST'])
def voice_webhook():
    greeting = ("Namaste! Welcome to Ray of Trust NGO. "
                "I am Aasha, your AI assistant. "
                "How can I help you with donations, shelter campaigns, or birthday celebrations today?")
    
    twiml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Gather input="speech" timeout="5" speechTimeout="auto" action="/api/voice/gather" method="POST">
        <Say voice="Polly.Aditi">{greeting}</Say>
    </Gather>
    <Say voice="Polly.Aditi">We did not hear any response. Thank you for calling Ray of Trust NGO. Goodbye!</Say>
</Response>"""
    return twiml_response, 200, {'Content-Type': 'application/xml; charset=utf-8'}

@app.route('/api/voice/gather', methods=['POST'])
def voice_gather():
    speech_result = request.values.get('SpeechResult', '').strip()
    caller = request.values.get('From', 'Caller')

    if speech_result:
        bot_response = generate_ai_response(speech_result, channel='voice')
        log_ai_conversation('voice', caller, speech_result, bot_response)
    else:
        bot_response = "I couldn't quite capture that. Could you please repeat your question?"

    twiml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Gather input="speech" timeout="5" speechTimeout="auto" action="/api/voice/gather" method="POST">
        <Say voice="Polly.Aditi">{bot_response}</Say>
    </Gather>
    <Say voice="Polly.Aditi">Thank you for contacting Ray of Trust NGO. Have a wonderful day!</Say>
</Response>"""
    return twiml_response, 200, {'Content-Type': 'application/xml; charset=utf-8'}

def detect_redirect_target(query):
    q = query.lower()
    # Explicitly block Admin Section access
    if any(k in q for k in ['admin', 'administrator', 'admin panel', 'manage db', 'delete campaign', 'admin login']):
        return 'RESTRICTED', 'Admin Access Restricted'
        
    if any(k in q for k in ['organize', 'start campaign', 'host drive', 'create campaign']):
        return '/campaigns', 'Organize Campaign Hub'
    elif any(k in q for k in ['campaign', 'drive', 'project', 'initiative', 'wakad', 'science kit', 'diwali smiles']):
        return '/campaigns', 'Campaigns Hub'
    elif any(k in q for k in ['donate', 'donation', 'payment', 'upi', 'stripe', 'money', '80g', 'tax', 'deduction']):
        return '/donate', 'Donation & 80G Portal'
    elif any(k in q for k in ['celebrate', 'birthday', 'kid', 'child', 'children', 'party', 'occasion', 'anniversary', 'cake']):
        return '/celebrate', 'Shelter Celebration Page'
    elif any(k in q for k in ['login', 'portal', 'receipt', 'history', 'account', 'my donation']):
        return '/donor_login', 'Donor Portal'
    elif any(k in q for k in ['home', 'about', 'overview', 'audit', 'impact', 'mission', 'ray of trust']):
        return '/', 'Home Overview'
    return None, None

@app.route('/api/ai_chat', methods=['POST'])
def api_ai_chat():
    data = request.get_json(silent=True) or request.form
    user_message = data.get('message', '').strip()
    selected_language = data.get('language', 'English').strip()

    if not user_message:
        return jsonify({'success': False, 'error': 'Empty message'}), 400

    sender_id = session.get('donor_id', 'Guest_Web_User')
    redirect_url, section_name = detect_redirect_target(user_message)

    if redirect_url == 'RESTRICTED':
        bot_response = ("🔒 **Admin Section Restricted**\n\n"
                        "The Admin Dashboard is strictly reserved for authorized NGO administrators. "
                        "I can assist you with all public features: making a donation, downloading 80G tax receipts, "
                        "exploring active campaigns, or sponsoring birthday celebrations for shelter kids!")
        redirect_url = None
    else:
        bot_response = generate_ai_response(user_message, channel='web', language=selected_language)

    log_ai_conversation('web', str(sender_id), user_message, bot_response)

    return jsonify({
        'success': True,
        'response': bot_response,
        'redirect_url': redirect_url,
        'section_name': section_name
    })

@app.route('/admin/ai_logs')
def admin_ai_logs():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM ai_conversation_logs ORDER BY id DESC LIMIT 100')
    logs = cursor.fetchall()
    return render_template('admin.html', ai_logs=logs, active_tab='ai_logs')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
