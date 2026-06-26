from app import app, get_conn

EMAIL = 'autotest@example.com'

def cleanup():
    try:
        conn = get_conn(); cur = conn.cursor()
        cur.execute('DELETE FROM users WHERE email=%s', (EMAIL,))
        conn.commit(); cur.close(); conn.close()
        print('Cleaned up existing test user (if any).')
    except Exception as e:
        print('Cleanup error:', e)


def run():
    cleanup()
    c = app.test_client()
    print('Registering...')
    r = c.post('/register', data={'name':'AutoTest','email':EMAIL,'password':'Secret123'}, follow_redirects=True)
    text = r.get_data(as_text=True)
    print('REGISTER status:', r.status_code)
    print('REGISTER page snippet:', text[:300].replace('\n',' '))

    print('\nLogging in...')
    r2 = c.post('/login', data={'email':EMAIL,'password':'Secret123'}, follow_redirects=True)
    text2 = r2.get_data(as_text=True)
    print('LOGIN status:', r2.status_code)
    print('LOGIN page snippet:', text2[:300].replace('\n',' '))

    print('\nLogging out...')
    r3 = c.get('/logout', follow_redirects=True)
    print('LOGOUT status:', r3.status_code)

if __name__ == '__main__':
    run()
