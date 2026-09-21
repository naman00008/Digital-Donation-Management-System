# Digital Donation Management System (RayOfTrust)

A transparent, secure, and modern NGO Donation Management web application built with Python Flask and SQLite.

---

## 🌟 Key Features

1. **Public Donor Experience**:
   - **Hero & Mission**: Impact showcase with interactive transparency modals.
   - **Multi-Method Payment Gateway**: Razorpay/Stripe-styled checkout with Dynamic QR Code generator for UPI, Credit/Debit Card input, Net Banking selector, and NEFT/RTGS wire transfer details with OTP simulation.
   - **Automated 80G Tax Receipts**: Instantly generated printable and downloadable 80G tax exemption receipts with official NGO stamp and signature.

2. **Donor Portal**:
   - Passwordless email login for registered donors.
   - Live donation history and campaign status tracking.
   - Impact tracker showing how donations were utilized (e.g., educational books, food distribution, medical supplies).
   - One-click receipt download for past donations.

3. **Admin Dashboard & Analytics**:
   - Secure Admin authentication (`admin` / `admin123`).
   - Summary metric cards (Total Funds, Contributions, Unique Donors, Active Campaigns).
   - Monthly donation trends chart powered by Chart.js.
   - Top Donors Leaderboard.
   - Direct donation logging for offline contributions.
   - Master donation log with status updates and impact notes management.

4. **Celebrate with NGO Kids (`/celebrate`)**:
   - Direct sponsorship of celebrations (birthdays, anniversaries, remembrance).
   - Custom sponsorship amount input with preset chips.
   - Shelter home child spotlight directory with bios, aspirations, and favorite treats.
   - Printable & downloadable official Celebration Passes (`/celebration/<id>`) with verified stamp.
   - Unified blue theme styling.

5. **Community Campaigns & Drives Hub (`/campaigns`)**:
   - Donors can organise their own campaigns and drives for shelter kids.
   - Other community members and volunteers can join active or upcoming drives.
   - Automatic broadcast notification alert to all registered donors.
   - Real-time headcounts showing organizers how many members will be joining with them.
   - Organizer protection: organizers are not asked to join their own drives.

6. **Input Validation & Security**:
   - International country code selector (`+91`, `+114`, `+1`, `+44`, etc.) with strict 10-digit phone lock.
   - IDOR protection on receipt and celebration pass endpoints.
   - Parameterized SQL queries protecting against SQL Injection.

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.8+ installed on your machine.

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Application
```bash
python app.py
```

### 4. Access the Platform
- **Public Website**: Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your web browser.
- **Celebrate with Kids**: [http://127.0.0.1:5000/celebrate](http://127.0.0.1:5000/celebrate)
- **Campaigns & Drives**: [http://127.0.0.1:5000/campaigns](http://127.0.0.1:5000/campaigns)
- **Admin Login**: [http://127.0.0.1:5000/login](http://127.0.0.1:5000/login)
  - **Username**: `admin`
  - **Password**: `admin123`
- **Donor Login**: [http://127.0.0.1:5000/donor_login](http://127.0.0.1:5000/donor_login)
  - Enter any registered donor email address.

---

## 📂 Project Structure

```
NGO.DONAMTION.MANAGEMENT/
│
├── app.py                     # Flask backend routing, auth & SQLite controllers
├── rayoftrust.db              # SQLite database (with seed data)
├── requirements.txt           # Python dependencies
├── .gitignore                 # Standard Python gitignore
├── README.md                  # Documentation
│
├── static/
│   └── images/                # Campaign images and official stamp
│       ├── 1.jpg
│       ├── 2.jpg
│       ├── 3.jpg
│       ├── 4.jpg
│       ├── stamp.jpg
│       └── official_stamp.jpg
│
└── templates/                 # Jinja2 HTML templates
    ├── index.html             # Homepage with mission & spotlights
    ├── donate.html            # Public donation form & checkout
    ├── thank_you.html         # Post-donation success confirmation
    ├── celebrate.html         # Celebrate with Kids booking portal
    ├── celebration_pass.html  # Official digital celebration pass
    ├── campaigns.html         # Community drives hub (organise & join)
    ├── donor_login.html       # Donor email lookup login
    ├── donor.html             # Donor dashboard & participations
    ├── login.html             # Admin login page
    ├── admin.html             # Admin analytics & campaign command hub
    └── receipt.html           # 80G official donation tax receipt
```
