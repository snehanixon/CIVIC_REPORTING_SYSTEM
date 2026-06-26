import mysql.connector
from werkzeug.security import generate_password_hash
import os
from datetime import datetime, timedelta

# MySQL connection configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Merlyn@12345',
    'database': 'civic_reporting',
    'auth_plugin': 'mysql_native_password'
}

# Connect to database
conn = mysql.connector.connect(**DB_CONFIG)
cur = conn.cursor()

# Add some sample users (besides admin)
sample_users = [
    ('John Smith', 'john@example.com', 'user123', 50),
    ('Maria Garcia', 'maria@example.com', 'user123', 75),
    ('Steve Wilson', 'steve@example.com', 'user123', 30)
]

print("Adding sample users...")
for name, email, password, points in sample_users:
    try:
        cur.execute('SELECT id FROM users WHERE email = %s', (email,))
        if cur.fetchone() is None:
            # Create new user
            password_hash = generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)
            cur.execute('''
                INSERT INTO users (name, email, password_hash, points)
                VALUES (%s, %s, %s, %s)
            ''', (name, email, password_hash, points))
            print(f"Created user: {email} (password: {password})")
    except Exception as e:
        print(f"Error creating user {email}: {e}")

# Get user IDs for reports
cur.execute('SELECT id, email FROM users WHERE email != %s', ('admin@example.com',))
user_ids = {email: id for id, email in cur.fetchall()}

# Add some sample reports
sample_reports = [
    ('Broken Streetlight', 'Streetlights', '123 Main St', 'Light has been out for 3 days', 'john@example.com', 'resolved'),
    ('Garbage Overflow', 'Garbage', '456 Oak Ave', 'Bins are overflowing', 'maria@example.com', 'in_progress'),
    ('Pothole Hazard', 'Roads', '789 Pine St', 'Large pothole damaging vehicles', 'steve@example.com', 'open'),
    ('Water Leak', 'Water', '321 Elm St', 'Water leaking from main', 'john@example.com', 'open'),
    ('Tree Branch Risk', 'Trees', '654 Maple Dr', 'Large branch about to fall', 'maria@example.com', 'resolved')
]

print("\nAdding sample reports...")
for title, category, location, desc, user_email, status in sample_reports:
    try:
        user_id = user_ids.get(user_email)
        if user_id:
            # Create report with somewhat random dates (within last 30 days)
            days_ago = abs(hash(title)) % 30  # Use title hash for deterministic but varied dates
            report_date = datetime.now() - timedelta(days=days_ago)
            cur.execute('''
                INSERT INTO reports (user_id, title, category, location, description, status, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (user_id, title, category, location, desc, status, report_date))
            print(f"Created report: {title}")
    except Exception as e:
        print(f"Error creating report {title}: {e}")

conn.commit()
cur.close()
conn.close()

print("\nSample data added successfully!")
print("\nYou can now log in with any of these accounts:")
print("Admin - admin@example.com / admin123")
for name, email, password, _ in sample_users:
    print(f"User - {email} / {password}")