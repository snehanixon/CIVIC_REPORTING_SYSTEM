Civic Reporting System - Colourful Dark Theme
--------------------------------------------
Features:
- Flask backend, MySQL database
- Separate User and Admin login
- Register, Login, Submit reports with image upload
- "My Reports" for users; Admin dashboard to change status
- Dark theme with colourful animated gradients, reveal animations and counters

Quick start (local):
1. Create and activate a virtualenv:
   python -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\Activate.ps1

2. Install dependencies:
   pip install -r requirements.txt

3. Create MySQL database and tables:
   mysql -u root -p < schema.sql

4. Set environment variables (or edit DB config in app.py):
   export DB_HOST=localhost
   export DB_USER=root
   export DB_PASSWORD=yourpassword
   export DB_NAME=civic_reporting

5. Run the app:
   export FLASK_APP=app.py
   flask run --host=0.0.0.0 --port=5000

Notes:
- This is a demo scaffold, not production-ready.
- Secure secrets, add CSRF protection, input sanitization and authentication hardening before deploying.
