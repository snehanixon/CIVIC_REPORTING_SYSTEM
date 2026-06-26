import mysql.connector
from werkzeug.security import generate_password_hash
import os

# MySQL connection configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Merlyn@12345',
    'database': 'civic_reporting',
    'auth_plugin': 'mysql_native_password'
}

# Create admin user
conn = mysql.connector.connect(**DB_CONFIG)
cur = conn.cursor()

# Admin credentials
admin_email = 'admin@example.com'
admin_password = 'admin123'
admin_name = 'Site Admin'
password_hash = generate_password_hash(admin_password, method='pbkdf2:sha256', salt_length=8)

try:
    # Check if admin already exists
    cur.execute('SELECT id FROM users WHERE email = %s', (admin_email,))
    if cur.fetchone() is None:
        # Create new admin user
        cur.execute('''
            INSERT INTO users (name, email, password_hash, is_admin, points)
            VALUES (%s, %s, %s, TRUE, 0)
        ''', (admin_name, admin_email, password_hash))
        conn.commit()
        print(f"Admin user created successfully!")
        print(f"Email: {admin_email}")
        print(f"Password: {admin_password}")
    else:
        print("Admin user already exists!")

except Exception as e:
    print(f"Error creating admin: {e}")

cur.close()
conn.close()