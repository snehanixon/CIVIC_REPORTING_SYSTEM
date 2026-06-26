import mysql.connector
import os

# MySQL connection configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Merlyn@12345',  # Using the password from your app.py
    'database': 'civic_reporting',
    'auth_plugin': 'mysql_native_password'
}

# Create fresh database with correct schema
conn = mysql.connector.connect(**DB_CONFIG)
cur = conn.cursor()

# Create users table with points column
cur.execute('''
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE,
    points INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

# Create reports table
cur.execute('''
CREATE TABLE reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    title VARCHAR(255) NOT NULL,
    category VARCHAR(50),
    location VARCHAR(255),
    description TEXT,
    image_path VARCHAR(255),
    status VARCHAR(20) DEFAULT 'open',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
)
''')

conn.commit()
cur.close()
conn.close()

print("Database initialized successfully with all required tables and columns.")