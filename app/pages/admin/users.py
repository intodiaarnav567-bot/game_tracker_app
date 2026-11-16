import pandas as pd
import streamlit as st
from app import auth, ui
from app.services import catalog, gamer, publisher, admin
account = auth.require_role('admin')
ui.page_header('Users', 'Accounts and access')
rows=admin.accounts()
search=st.text_input('Search users',key='admin_user_search')
ui.table([r for r in rows if search.lower() in r['username'].lower()],'admin_users')
roles = {'gamer': 'Gamer', 'game_publisher': 'Game Publisher', 'admin': 'Admin'}
role = st.selectbox('New account role', list(roles), format_func=roles.get, key='new_account_role')
publisher_id = None
if role == 'game_publisher':
    publishers = {row['id']: row['name'] for row in catalog.reference('Publisher')}
    publisher_choice = st.selectbox(
        'Publisher', [*publishers, 'new'],
        format_func=lambda identifier: publishers.get(identifier, 'Create new publisher'),
        key='new_publisher_link',
    )
    if publisher_choice != 'new':
        publisher_id = publisher_choice
with st.form('create_account_'+str(st.session_state.form_version)):
    username=st.text_input('Username',max_chars=100,key='new_username')
    email=st.text_input('Email',max_chars=255,key='new_email')
    password=st.text_input('Password',type='password',key='new_password')
    user_id=None
    new_publisher_name = None
    if role=='gamer':
        options={r['user_id']:f"{r['username']} ({r['user_id']})" for r in admin.users() if r['user_id'] not in [a['user_id'] for a in rows]}
        user_id=st.selectbox('Player',[None,*options],format_func=lambda x:options.get(x,'Create new player'),key='new_user_link')
    if role == 'game_publisher' and publisher_id is None:
        new_publisher_name = st.text_input(
            'New publisher name', max_chars=200, key='new_publisher_name'
        )
    if st.form_submit_button('Create account',key='create_account_submit',type='primary'):
        ui.action(admin.create_account, username, email, password, role, user_id, publisher_id,
                  new_publisher_name)
with st.expander('Create new developer'):
    with st.form('create_developer', clear_on_submit=True):
        developer_name = st.text_input('Developer name', max_chars=200, key='new_developer_name')
        if st.form_submit_button('Create developer', key='create_developer_submit'):
            ui.action(admin.catalog_save, 'Developer', None, developer_name)
options={r['account_id']:r for r in rows}
if options:
    identifier=st.selectbox('Manage account',options,format_func=lambda x:options[x]['username'],key='manage_account')
    selected=options[identifier]
    if st.button('Deactivate' if selected['is_active'] else 'Activate',key='account_active'):
        ui.confirm_dialog('Change this account’s access?',admin.set_active,identifier,not selected['is_active'])
    with st.form('reset_password_form'):
        password=st.text_input('New password',type='password',key='reset_password')
        if st.form_submit_button('Reset password',key='reset_password_submit'):
            ui.action(admin.reset_password,identifier,password)
    if st.button('Delete account',key='account_delete'):
        ui.confirm_dialog('Delete this account and its player profile?',admin.delete_account,identifier)
