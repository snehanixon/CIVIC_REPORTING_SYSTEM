"""Create or promote a user to admin for the CivicHub app.

Usage (PowerShell examples):
# create a new admin user
F:\mss\.venv\Scripts\python.exe f:\mss\make_admin.py --name "Admin User" --email admin@example.com --password Secret123

# promote an existing user to admin (keeps password unchanged unless --password provided)
F:\mss\.venv\Scripts\python.exe f:\mss\make_admin.py --email user@example.com --promote
"""
import argparse
from werkzeug.security import generate_password_hash

# import the app's DB helper
from app import get_conn


def normalize_row(row):
    if row is None:
        return None
    if isinstance(row, dict):
        return row
    # tuple-like: convert to dict by using index positions when needed
    return row


def main():
    p = argparse.ArgumentParser(description='Create or promote an admin user')
    p.add_argument('--name', help='Full name for the user', default='Administrator')
    p.add_argument('--email', required=True, help='Email for the user')
    p.add_argument('--password', help='Password for the user (if creating or updating)')
    p.add_argument('--promote', action='store_true', help='Promote existing user to admin')
    args = p.parse_args()

    email = args.email.strip().lower()
    name = args.name.strip()

    if not (args.password or args.promote):
        # if promoting only, password optional; if creating, password required
        # but we allow creating without password to prompt for it
        pass

    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute('SELECT id, email FROM users WHERE email=%s', (email,))
        row = cur.fetchone()
        exists = row is not None
        if exists:
            # get id value from dict or tuple
            uid = row['id'] if isinstance(row, dict) and 'id' in row else (row[0] if isinstance(row, (list, tuple)) else None)
            if args.password:
                pw_hash = generate_password_hash(args.password)
                cur.execute('UPDATE users SET name=%s, password_hash=%s, is_admin=1 WHERE id=%s', (name, pw_hash, uid))
                print(f'Updated user {email} and granted admin (password updated).')
            else:
                cur.execute('UPDATE users SET name=%s, is_admin=1 WHERE id=%s', (name, uid))
                print(f'Promoted existing user {email} to admin.')
        else:
            if not args.password:
                raise SystemExit('User does not exist; please provide --password to create a new admin user.')
            pw_hash = generate_password_hash(args.password)
            cur.execute('INSERT INTO users (name,email,password_hash,is_admin) VALUES (%s,%s,%s,1)', (name, email, pw_hash))
            print(f'Created new admin user {email}.')
        conn.commit()
    except Exception as e:
        print('Error:', e)
    finally:
        try:
            cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass


if __name__ == '__main__':
    main()
#F:/mss/.venv/Scripts/python.exe f:/mss/make_admin.py --name "Site Admin" --email admin@example.com --password AdminPass123