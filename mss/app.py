import os, uuid, io
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory, abort, send_file
import sqlite3
import qrcode
try:
    import mysql.connector
    from mysql.connector import pooling
    HAS_MYSQL = True
except Exception:
    mysql = None
    pooling = None
    HAS_MYSQL = False
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = os.path.dirname(__file__)
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXT = {'png','jpg','jpeg','gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.',1)[1].lower() in ALLOWED_EXT

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET', 'dev-secret-key')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5 MB max

DB_CONFIG = {
    'host': os.environ.get('DB_HOST','localhost'),
    'user': os.environ.get('DB_USER','root'),
    'password': os.environ.get('DB_PASSWORD','Merlyn@12345'),
    'database': os.environ.get('DB_NAME','civic_reporting'),
    'auth_plugin': 'mysql_native_password'
}

# Try to create a MySQL connection pool if mysql connector is available and configured
pool = None
USE_SQLITE = False
SQLITE_PATH = os.path.join(BASE_DIR, 'data.db')
if HAS_MYSQL:
    try:
        pool = pooling.MySQLConnectionPool(pool_name='mypool', pool_size=5, **DB_CONFIG)
    except Exception as e:
        pool = None
        print('Warning: could not create MySQL pool (check DB settings). Falling back to SQLite.', e)
        USE_SQLITE = True
else:
    print('mysql-connector-python not available; using SQLite fallback.')
    USE_SQLITE = True


class SQLiteCursor:
    def __init__(self, conn):
        self._cur = conn.cursor()

    def execute(self, query, params=None):
        # convert MySQL style %s placeholders to SQLite ?
        if params is None:
            params = ()
        q = query.replace('%s', '?')
        return self._cur.execute(q, params)

    def fetchone(self):
        row = self._cur.fetchone()
        if row is None:
            return None
        cols = [d[0] for d in self._cur.description]
        return dict(zip(cols, row))

    def fetchall(self):
        rows = self._cur.fetchall()
        cols = [d[0] for d in self._cur.description] if self._cur.description else []
        return [dict(zip(cols, r)) for r in rows]

    def close(self):
        try:
            self._cur.close()
        except Exception:
            pass

    @property
    def description(self):
        return self._cur.description


class SQLiteConnectionWrapper:
    def __init__(self, path):
        self._conn = sqlite3.connect(path, check_same_thread=False)

    def cursor(self, dictionary=False):
        return SQLiteCursor(self._conn)

    def commit(self):
        return self._conn.commit()

    def close(self):
        try:
            self._conn.close()
        except Exception:
            pass


def init_sqlite_db(path):
    # create tables if they do not exist (SQLite dialect)
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      email TEXT NOT NULL UNIQUE,
      password_hash TEXT NOT NULL,
      is_admin INTEGER DEFAULT 0,
      points INTEGER DEFAULT 0,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    ''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS reports (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER,
      title TEXT NOT NULL,
      category TEXT,
      location TEXT,
      description TEXT,
      image_path TEXT,
      status TEXT DEFAULT 'open',
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
    );
    ''')
    conn.commit(); cur.close(); conn.close()


def ensure_points_column():
    """Ensure 'points' column exists in users table for MySQL deployments."""
    try:
        conn = None
        if USE_SQLITE:
            # SQLite init already included points
            return
        # try to get a connection and ALTER TABLE to add column if missing
        conn = get_conn(); cur = conn.cursor()
        try:
            cur.execute("ALTER TABLE users ADD COLUMN points INT DEFAULT 0")
            conn.commit()
        except Exception:
            # column probably exists or not applicable; ignore
            pass
        try:
            cur.close()
        except Exception:
            pass
    except Exception:
        pass
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass


# map feature removed


def get_conn():
    if not USE_SQLITE and pool is None and HAS_MYSQL:
        # try single connection
        return mysql.connector.connect(**DB_CONFIG)
    if not USE_SQLITE and pool is not None:
        return pool.get_connection()
    # SQLite fallback
    # ensure DB exists and tables created
    if not os.path.exists(SQLITE_PATH):
        init_sqlite_db(SQLITE_PATH)
    return SQLiteConnectionWrapper(SQLITE_PATH)

CATEGORIES = ['Roads','Streetlights','Garbage','Water','Sanitation','Trees','Other']

def current_user():
    uid = session.get('user_id')
    if not uid:
        return None
    conn = get_conn(); cur = conn.cursor(dictionary=True)
    cur.execute('SELECT id,name,email,is_admin,points FROM users WHERE id=%s', (uid,))
    u = cur.fetchone()
    cur.close(); conn.close()
    return u

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/qr-code')
def generate_qr():
    # Use the ngrok URL
    website_url = "https://triply-uliginous-mathilde.ngrok-free.dev"
    
    # Create QR code instance
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    
    # Add the data
    qr.add_data(website_url)
    qr.make(fit=True)

    # Create the QR code image
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Save it to a bytes buffer
    img_buffer = io.BytesIO()
    img.save(img_buffer, 'PNG')
    img_buffer.seek(0)
    
    return send_file(img_buffer, mimetype='image/png')

@app.route('/')
def index():
    users_count = 0
    resolved_count = 0
    active_count = 0
    top_users = []
    max_points = 1
    try:
        conn = get_conn(); cur = conn.cursor()
        # Get all counts in a single transaction
        cur.execute('''
            SELECT
                (SELECT COUNT(*) FROM users) as users_count,
                (SELECT COUNT(*) FROM reports WHERE status='resolved') as resolved_count,
                (SELECT COUNT(*) FROM reports WHERE status<>'resolved') as active_count
        ''')
        counts = cur.fetchone()
        if counts:
            if isinstance(counts, dict):
                users_count = counts['users_count']
                resolved_count = counts['resolved_count']
                active_count = counts['active_count']
            else:
                users_count = counts[0]
                resolved_count = counts[1]
                active_count = counts[2]

        # get top 5 non-admin users by points
        try:
            cur.execute("SELECT id,name,points FROM users WHERE COALESCE(is_admin,0)=0 ORDER BY points DESC LIMIT 5")
            rows = cur.fetchall()
            if rows:
                for r in rows:
                    if isinstance(r, dict):
                        top_users.append({'id': r.get('id'), 'name': r.get('name'), 'points': r.get('points') or 0})
                    else:
                        top_users.append({'id': r[0], 'name': r[1], 'points': r[2] or 0})
            if top_users:
                max_points = max(u['points'] for u in top_users) or 1
        except Exception:
            top_users = []
            max_points = 1

        cur.close(); conn.close()
    except Exception:
        # DB may not be set up yet
        top_users = []
        max_points = 1

    return render_template('index.html', users_count=users_count, resolved_count=resolved_count, active_count=active_count, top_users=top_users, max_points=max_points, user=current_user())

@app.route('/about')
def about():
    return render_template('about.html', user=current_user())


@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name','').strip()
        email = request.form.get('email','').strip().lower()
        password = request.form.get('password','')
        if not name or not email or not password:
            flash('Please fill all fields.', 'danger'); return redirect(url_for('register'))
        pw_hash = generate_password_hash(password)
        try:
            conn = get_conn(); cur = conn.cursor()
            cur.execute('INSERT INTO users (name,email,password_hash) VALUES (%s,%s,%s)', (name,email,pw_hash))
            conn.commit(); cur.close(); conn.close()
            flash('Registration successful. Please login.', 'success')
            return redirect(url_for('login'))
        except mysql.connector.IntegrityError:
            flash('Email already registered. Please login or use a different email.', 'danger')
            return redirect(url_for('register'))
        except Exception as e:
            flash('An error occurred during registration.', 'danger')
            return redirect(url_for('register'))
    return render_template('register.html', user=current_user())

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email','').strip().lower()
        password = request.form.get('password','')
        if not email or not password:
            flash('Please enter both email and password.', 'danger'); return redirect(url_for('login'))
        try:
            conn = get_conn(); cur = conn.cursor(dictionary=True)
            cur.execute('SELECT id,name,email,password_hash,is_admin FROM users WHERE email=%s', (email,))
            user = cur.fetchone(); cur.close(); conn.close()
            if not user or not check_password_hash(user['password_hash'], password):
                flash('Invalid email or password.', 'danger'); return redirect(url_for('login'))
            # success
            session.clear(); session['user_id'] = user['id']
            flash(f'Welcome back, {user["name"]}!', 'success')
            if user.get('is_admin'):
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('index'))
        except Exception as e:
            flash('An error occurred while logging in.', 'danger'); return redirect(url_for('login'))
    return render_template('login.html', user=current_user())

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('index'))


@app.route('/new-report', methods=['GET','POST'])
def new_report():
    user = current_user()
    if not user:
        flash('Please login to submit reports.', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form.get('title','').strip()
        category = request.form.get('category','Other')
        location = request.form.get('location','').strip()
        description = request.form.get('description','').strip()
        file = request.files.get('image')
        img_path = None
        if file and file.filename:
            if allowed_file(file.filename):
                filename = secure_filename(file.filename)
                unique = f"{uuid.uuid4().hex}_{filename}"
                saved = os.path.join(app.config['UPLOAD_FOLDER'], unique)
                file.save(saved)
                img_path = unique
            else:
                flash('File type not allowed.', 'danger')
                return redirect(url_for('new_report'))
        try:
            conn = get_conn(); cur = conn.cursor()
            cur.execute('INSERT INTO reports (user_id,title,category,location,description,image_path) VALUES (%s,%s,%s,%s,%s,%s)',
                        (user['id'], title, category, location, description, img_path))
            conn.commit(); cur.close(); conn.close()
            flash('Report submitted. Thank you!', 'success')
            return redirect(url_for('my_reports'))
        except Exception:
            flash('Could not submit report.', 'danger')
            return redirect(url_for('new_report'))
    return render_template('new_report.html', categories=CATEGORIES, user=user)

@app.route('/my-reports')
def my_reports():
    user = current_user()
    if not user:
        flash('Please login', 'danger'); return redirect(url_for('login'))
    rows = []
    try:
        conn = get_conn(); cur = conn.cursor(dictionary=True)
        cur.execute('SELECT * FROM reports WHERE user_id=%s ORDER BY created_at DESC', (user['id'],))
        rows = cur.fetchall(); cur.close(); conn.close()
    except Exception:
        pass
    return render_template('my_reports.html', reports=rows, user=user)

@app.route('/admin/login', methods=['GET','POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form.get('email','admin@example.com').strip().lower()
        password = request.form.get('password','admin123')
        if not email or not password:
            flash('Please enter both email and password.', 'danger'); return redirect(url_for('admin_login'))
        try:
            conn = get_conn(); cur = conn.cursor(dictionary=True)
            cur.execute('SELECT id,name,email,password_hash,is_admin FROM users WHERE email=%s', (email,))
            user = cur.fetchone(); cur.close(); conn.close()
            if not user or not user.get('is_admin') or not check_password_hash(user['password_hash'], password):
                flash('Invalid admin credentials.', 'danger'); return redirect(url_for('admin_login'))
            session.clear(); session['user_id'] = user['id']
            flash('Admin logged in.', 'success'); return redirect(url_for('admin_dashboard'))
        except Exception:
            flash('An error occurred during admin login.', 'danger'); return redirect(url_for('admin_login'))
    return render_template('admin_login.html', user=current_user())

def admin_required():
    u = current_user()
    if not u or not u.get('is_admin'):
        abort(403)

@app.route('/admin')
def admin_dashboard():
    admin_required()
    rows = []
    try:
        conn = get_conn(); cur = conn.cursor(dictionary=True)
        cur.execute('SELECT r.*, u.name as user_name FROM reports r LEFT JOIN users u ON r.user_id=u.id ORDER BY r.created_at DESC')
        rows = cur.fetchall(); cur.close(); conn.close()
    except Exception:
        pass
    return render_template('admin_dashboard.html', reports=rows, user=current_user())

@app.route('/admin/status/<int:report_id>/<string:status>', methods=['POST'])
def admin_status(report_id,status):
    admin_required()
    if status not in ('open','in_progress','resolved'):
        flash('Invalid status', 'danger'); return redirect(url_for('admin_dashboard'))
    try:
        conn = get_conn(); cur = conn.cursor()
        # if resolving and points provided, award to report's user
        points = 0
        if status == 'resolved':
            try:
                points = int(request.form.get('points') or 0)
            except Exception:
                points = 0
        cur.execute('UPDATE reports SET status=%s WHERE id=%s', (status, report_id))
        if status == 'resolved' and points>0:
            # find user_id
            cur.execute('SELECT user_id FROM reports WHERE id=%s', (report_id,))
            row = cur.fetchone()
            uid = None
            if isinstance(row, dict):
                uid = row.get('user_id')
            elif row:
                uid = row[0]
            if uid:
                # add points to user
                # use DB-specific SQL; try generic UPDATE
                try:
                    cur.execute('UPDATE users SET points = COALESCE(points,0) + %s WHERE id=%s', (points, uid))
                except Exception:
                    # fallback for SQLite (uses ? placeholders handled by wrapper)
                    cur.execute('UPDATE users SET points = COALESCE(points,0) + ? WHERE id=?', (points, uid))
        conn.commit(); cur.close(); conn.close()
        flash('Status updated', 'success')
    except Exception as e:
        print('admin_status error:', e)
        flash('Could not update status.', 'danger')
    if request.args.get('redirect') == 'home':
        return redirect(url_for('index'))
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    # ensure points column exists for non-SQLite DBs
    ensure_points_column()
    app.run(host='0.0.0.0', port=5000, debug=True)
