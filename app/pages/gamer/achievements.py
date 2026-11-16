import pandas as pd
import streamlit as st
from app import auth, ui
from app.services import catalog, gamer, publisher, admin
account = auth.require_role('gamer')
ui.page_header('Achievements', 'Track your milestones')
rows = gamer.achievements()
earned = [r for r in rows if r['unlock_time']]
ui.metrics([('Earned', len(earned)), ('Points', sum(r['points'] or 0 for r in earned))])
games = {g['appid']:g['name'] for g in gamer.library() if g['ownership_status']!='wishlist'}
if games:
    appid = st.selectbox('Game',games,format_func=games.get,key='gamer_achievement_game')
    selected = [r for r in rows if r['appid']==appid]
    count = sum(bool(r['unlock_time']) for r in selected)
    st.progress(count/len(selected) if selected else 0,text=f'{count} / {len(selected)} earned')
    for item in ui.paginate(selected,'gamer_achievements'):
        hidden = item['hidden'] and not item['unlock_time']
        st.write('Hidden achievement' if hidden else item['achievement_name'])
        st.caption(ui.fmt_date(item['unlock_time']) if item['unlock_time'] else 'Locked')
        if st.button('Mark as unlocked', key=f'unlock_{item["achievement_id"]}',disabled=bool(item['unlock_time']),help='Already earned.' if item['unlock_time'] else None):
            ui.action(gamer.unlock,appid,item['achievement_id'])
else:
    ui.empty_state()
