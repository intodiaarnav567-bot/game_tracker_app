import pandas as pd
import streamlit as st
from app import auth, ui
from app.services import catalog, gamer, publisher, admin
account = auth.require_role('game_publisher')
ui.page_header('Achievements', 'Manage game milestones')
games={g['appid']:g['name'] for g in publisher.games()}
if games:
    appid=st.selectbox('Game',games,format_func=games.get,key='pub_achievement_game')
    rows=catalog.achievements(appid)
    ui.table(rows,'pub_achievements')
    options={r['achievement_id']:r for r in rows}
    identifier=st.selectbox('Achievement',[None,*options],format_func=lambda x: options[x]['achievement_name'] if x else 'Add achievement',key=f'pub_achievement_select_{appid}')
    selected=options.get(identifier,{})
    key=f'pub_ach_{appid}_{identifier}_{st.session_state.form_version}'
    with st.form(key):
        name=st.text_input('Name',value=selected.get('achievement_name',''),max_chars=200,key=key+'_name')
        description=st.text_area('Description',value=selected.get('description') or '',key=key+'_description')
        points=st.number_input('Points',min_value=0,value=int(selected.get('points') or 0),key=key+'_points')
        hidden=st.checkbox('Hidden',value=bool(selected.get('hidden')),key=key+'_hidden')
        if st.form_submit_button('Save achievement',key=key+'_save',type='primary'):
            if not name.strip():
                st.error('Enter an achievement name.')
            else:
                ui.action(publisher.save_achievement,appid,identifier,name,description,points,hidden)
    if st.button('Delete achievement',key='pub_ach_delete',disabled=identifier is None,help='Select an achievement first.' if identifier is None else None):
        ui.confirm_dialog('Delete this achievement and its earned history?',publisher.delete_achievement,appid,identifier)
else:
    ui.empty_state('Add a game first.')
