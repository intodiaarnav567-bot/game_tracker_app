import pandas as pd
import streamlit as st
from app import auth, ui
from app.services import catalog, gamer, publisher, admin
account = auth.require_role('admin')
ui.page_header('Games', 'Manage the game catalog')
if not ui.detail():
    games=catalog.games()
    search=st.text_input('Search games',key='admin_games_search')
    ui.table([g for g in games if search.lower() in g['name'].lower()],'admin_games')
    options={g['appid']:g for g in games}
    appid=st.selectbox('Game',[None,*options],format_func=lambda x: options[x]['name'] if x else 'Add game',key='admin_game_select')
    ui.game_form(options.get(appid))
    if appid:
        game=options[appid]
        label='Delist' if game['is_active'] else 'Relist'
        if st.button(label,key='admin_game_active'):
            ui.confirm_dialog(label+' this game?',admin.active,appid,not game['is_active'])
        if st.button('View game',key='admin_game_detail'):
            st.session_state.selected_appid=appid
            st.rerun()
