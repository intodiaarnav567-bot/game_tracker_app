import time

import bcrypt
import streamlit as st

from app import db


def initialize():
    for key, value in {'account': None, 'failed_logins': 0, 'locked_until': 0,
                       'selected_appid': None, 'flash': None, 'busy': False,
                       'page_numbers': {}, 'form_version': 0, 'current_page': None}.items():
        st.session_state.setdefault(key, value)


def hash_password(password):
    if not 8 <= len(password.encode('utf-8')) <= 72:
        raise ValueError('Password must contain 8 to 72 UTF-8 bytes.')
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def login(username, password):
    if time.time() < st.session_state.locked_until:
        raise ValueError('Too many attempts. Please wait five minutes.')
    rows = db.query('login', 'SELECT * FROM App_Account WHERE username=%s', (username.strip(),))
    valid = False
    if rows and rows[0]['is_active']:
        try:
            valid = bcrypt.checkpw(password.encode(), rows[0]['password_hash'].encode())
        except ValueError:
            pass
    if not valid:
        st.session_state.failed_logins += 1
        if st.session_state.failed_logins >= 5:
            st.session_state.locked_until = time.time() + 300
            st.session_state.failed_logins = 0
        raise ValueError('Incorrect username or password')
    account = rows[0]
    db.query('login', 'UPDATE App_Account SET last_login_at=CURRENT_TIMESTAMP WHERE account_id=%s',
             (account['account_id'],))
    account.pop('password_hash')
    st.session_state.account = account
    st.session_state.failed_logins = 0


def identity(*roles):
    account = st.session_state.get('account')
    if not account or (roles and account['role'] not in roles):
        raise PermissionError('You do not have access to this page.')
    return account


def require_role(*roles):
    try:
        return identity(*roles)
    except PermissionError:
        st.info('Please sign in with an account that can access this page.')
        st.stop()


def logout():
    st.session_state.clear()
    st.rerun()
