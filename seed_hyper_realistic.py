import sqlite3
import random
import datetime

# Realistic Indian Data
FIRST_NAMES = ["Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Ayaan", "Krishna", "Ishaan", "Shaurya", "Saanvi", "Aanya", "Aadhya", "Aaradhya", "Ananya", "Pari", "Diya", "Navya", "Neha", "Riya", "Naman", "Rahul", "Priya", "Anjali", "Vikram", "Siddharth", "Kavya", "Pooja", "Rohan", "Rishabh", "Kriti", "Sneha", "Aditi", "Karan", "Kunal"]
LAST_NAMES = ["Sharma", "Verma", "Patil", "Deshmukh", "Joshi", "Kulkarni", "Singh", "Yadav", "Gupta", "Choudhary", "Iyer", "Nair", "Reddy", "Rao", "Kumar", "Das", "Bose", "Chatterjee", "Banerjee", "Mehta", "Patel", "Shah", "Desai", "Agarwal", "Bansal"]
CORPORATES = ["Tata Group CSR", "Infosys Foundation", "Wipro Cares", "Reliance Foundation", "HDFC Bank CSR", "Mahindra Rise", "L&T Public Charitable Trust"]

PURPOSES = ["Child Education", "Shelter Nutrition", "Winter Clothes", "General Fund", "Skill Development", "Medical Emergency", "Clean Water Initiative", "Girl Child Education"]
IMPACTS = ["Supported 10 children's school fees", "Provided 50 winter blankets", "Funded emergency surgery for Aarush", "General operational support", "Purchased new books for the library", "Monthly ration for 20 families", "Installed 2 water purifiers", "Vocational training for 5 women", ""]

OCCASIONS = ["Birthday", "Anniversary", "Memorial Day", "Festival", "Corporate Milestone", "Graduation", "First Salary"]
PACKAGES = ["Sweet Joy & Cake Cutting (₹2,500)", "Nutritious Feast & Celebration Cake (₹5,000)", "Grand Happiness Day (₹10,000)", "Shelter Mega Party (₹25,000)"]
ATTENDANCE = ["In-Person Visit", "Live Video Call", "Request Photos/Videos Only"]

db = sqlite3.connect('rayoftrust.db')
c = db.cursor()

# 1. Generate 60 Users
user_ids = []
for _ in range(60):
    is_corp = random.random() < 0.1
    if is_corp:
        name = random.choice(CORPORATES)
    else:
        name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
    
    email = name.lower().replace(" ", ".") + f"{random.randint(10,999)}@gmail.com"
    phone = f"+91 {random.randint(7000000000, 9999999999)}"
    
    try:
        c.execute("INSERT INTO users (name, email, phone, password_hash, role) VALUES (?, ?, ?, ?, 'donor')", 
                  (name, email, phone, "hash"))
        user_ids.append(c.lastrowid)
    except sqlite3.IntegrityError:
        pass # Skip duplicate emails

# Fetch all user ids if some failed
c.execute("SELECT id, name, email, phone FROM users WHERE role='donor'")
all_users = c.fetchall()

# 2. Generate 300 Donations over the last 18 months
start_date = datetime.datetime.now() - datetime.timedelta(days=500)
for _ in range(300):
    user = random.choice(all_users)
    uid, uname, uemail, uphone = user
    
    # Generate random date
    days_to_add = random.randint(0, 500)
    d_date = (start_date + datetime.timedelta(days=days_to_add)).strftime('%Y-%m-%d')
    
    # Generate amount
    is_large = random.random() < 0.1
    if "Foundation" in uname or "CSR" in uname or "Trust" in uname:
        amount = random.choice([50000, 100000, 250000, 500000])
    elif is_large:
        amount = random.choice([10000, 15000, 20000, 25000])
    else:
        amount = random.choice([500, 1000, 1500, 2000, 2500, 3000, 5000])
        
    purpose = random.choice(PURPOSES)
    status = random.choice(["Received", "Utilized", "Tax Receipt Issued"])
    impact = random.choice(IMPACTS) if status != "Received" else ""
    
    c.execute("""
        INSERT INTO donations (donor_id, amount, date, purpose, status, impact_details)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (uid, amount, d_date, purpose, status, impact))

# 3. Generate 60 Celebrations over the last 6 months
start_date_cel = datetime.datetime.now() - datetime.timedelta(days=180)
for _ in range(60):
    user = random.choice(all_users)
    uid, uname, uemail, uphone = user
    
    days_to_add = random.randint(0, 180)
    c_date = (start_date_cel + datetime.timedelta(days=days_to_add)).strftime('%Y-%m-%d')
    created_at = (start_date_cel + datetime.timedelta(days=days_to_add - random.randint(1, 10))).strftime('%Y-%m-%d %H:%M:%S')
    
    occasion = random.choice(OCCASIONS)
    celebrant = random.choice(FIRST_NAMES) if occasion != "Corporate Milestone" else uname
    time_slot = random.choice(["10:00 AM - 12:00 PM (Morning Joy)", "01:00 PM - 03:00 PM (Lunch Feast & Cake)", "04:00 PM - 06:00 PM (Afternoon Feast)"])
    
    package = random.choice(PACKAGES)
    amt = float(package.split('₹')[1].replace(',', '').replace(')', ''))
    
    mode = random.choice(ATTENDANCE)
    msg = random.choice(["Bringing smiles to the kids!", "In loving memory.", "Happy to share our joy with you all.", ""])
    status = random.choice(["Confirmed", "Completed", "Completed", "Cancelled"])
    
    c.execute("""
        INSERT INTO celebrations (user_id, donor_name, donor_email, donor_phone, occasion_type, celebrant_name, celebration_date, time_slot, package_type, amount, attendance_mode, special_message, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (uid, uname, uemail, uphone, occasion, celebrant, c_date, time_slot, package, amt, mode, msg, status, created_at))

db.commit()
db.close()
print("Hyper-realistic database generated successfully!")
