import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import streamlit as st

from app import auth, config, ui

st.set_page_config(page_title='Game Collection', page_icon='🎮', layout='wide')
auth.initialize()
ui.theme()

def sign_in(username, password):
    try:
        auth.login(username, password)
    except ValueError as error:
        st.error(str(error))
    except Exception:
        logging.exception('Login failed')
        st.error('Something went wrong. Please try again.')
    else:
        st.rerun()


if not st.session_state.account:
    ui.page_header('Game Collection', 'Your games. Your achievements.')
    with st.container(border=True):
        username = st.text_input('Username', key='login_username')
        password = st.text_input('Password', type='password', key='login_password')
        if st.button('Login', type='primary', key='login_submit'):
            sign_in(username, password)
    if config.DEMO_MODE:
        with st.expander('Demo accounts'):
            for label, name, demo_password in (
                ('Gamer', 'gamer1', 'Gamer@123'),
                ('Game Publisher', 'pub_valve', 'Publisher@123'),
                ('Admin', 'admin', 'Admin@123'),
            ):
                st.caption(f'{name} / {demo_password}')
                if st.button(f'Sign in as {label}', key=f'demo_login_{name}'):
                    sign_in(name, demo_password)
    st.stop()


menus = {
    'gamer': [('store','🛒 Store'),('home','🏠 Home'),('library','📚 My Library'),
              ('wishlist','❤️ Wishlist'),('achievements','🏆 Achievements'),('profile','👤 Profile')],
    'game_publisher': [('dashboard','📊 Dashboard'),('games','🎮 My Games'),('add','➕ Add Game'),
                       ('achievements','🏆 Achievements'),('reviews','💬 Reviews')],
    'admin': [('overview','📊 Overview'),('users','👥 Users'),('games','🎮 Games'),
              ('catalog','🏷️ Catalog Data'),('purchases','💳 Purchases'),('reviews','💬 Reviews')],
}
account = auth.identity()
folder = 'publisher' if account['role'] == 'game_publisher' else account['role']
pages = [st.Page(f'pages/{folder}/{name}.py', title=label) for name, label in menus[account['role']]]
page = st.navigation(pages)
if st.session_state.current_page != page.url_path:
    st.session_state.selected_appid = None
    st.session_state.current_page = page.url_path
with st.sidebar:
    st.divider()
    st.write(account['username'])
    ui.badge(account['role'].replace('_', ' ').title())
    if st.button('Logout', key='logout'):
        auth.logout()
if st.session_state.flash:
    st.toast(st.session_state.flash)
    st.session_state.flash = None
try:
    with st.spinner('Loading…'):
        page.run()
except Exception:
    logging.exception('Page failed')
    st.error('Something went wrong. Please try again.')
