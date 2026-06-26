from app import get_conn, app
from werkzeug.security import check_password_hash

def main():
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute('SELECT id,name,email,password_hash,is_admin,created_at FROM users WHERE email=%s', ('admin@example.com',))
        row = cur.fetchone()
        print('DB ROW:', row)
        if not row:
            print('\n-> No admin user found in the database the app is using.')
            return
        # extract password_hash
        if isinstance(row, dict):
            pw_hash = row.get('password_hash')
            is_admin = row.get('is_admin')
        else:
            # tuple-like
            pw_hash = row[3] if len(row) > 3 else None
            is_admin = row[4] if len(row) > 4 else None
        print('is_admin field:', is_admin)
        print('password_hash present:', bool(pw_hash))
        if pw_hash:
            ok = check_password_hash(pw_hash, 'admin123')
            print("check_password_hash('admin123'):", ok)

        # Try admin login via test client
        with app.test_client() as c:
            resp = c.post('/admin/login', data={'email':'admin@example.com','password':'admin123'}, follow_redirects=True)
            print('\nAdmin login attempt HTTP status:', resp.status_code)
            body = resp.get_data(as_text=True)
            snippet = body[:1000].replace('\n',' ')
            print('Response snippet:', snippet)
            if 'Invalid admin credentials' in body:
                print('\nResponse contains invalid admin credentials message')
            if 'Admin logged in' in body or 'Admin Dashboard' in body:
                print('\nAdmin login appeared successful')
    except Exception as e:
        print('ERROR querying DB or testing login:', e)
    finally:
        try:
            cur.close()
        except:
            pass
        try:
            conn.close()
        except:
            pass

if __name__ == '__main__':
    main()
