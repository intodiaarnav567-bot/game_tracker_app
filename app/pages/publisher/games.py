import pandas as pd
import streamlit as st
from app import auth, ui
from app.services import catalog, gamer, publisher, admin
account = auth.require_role('game_publisher')
ui.page_header('My Games', 'Manage your catalog')
if not ui.detail():
    games=publisher.games()
    stats={r['appid']:r for r in publisher.stats()}
    for game in ui.paginate(games,'publisher_games'):
        st.image(ui.poster(game['appid'],game['header_image_url'],game['name']),width=460)
        st.subheader(game['name'])
        summary=stats[game['appid']]
        st.caption(f"{summary['owners']} owners · {summary['wishlists']} wishlists · {summary['review_count']} reviews")
        ui.badge('Active' if game['is_active'] else 'Delisted')
        with st.expander('Edit '+game['name']):
            ui.game_form(game)
        label='Delist' if game['is_active'] else 'Relist'
        if st.button(label,key=f'pub_active_{game["appid"]}'):
            ui.confirm_dialog(label+' this game?',publisher.active,game['appid'],not game['is_active'])
        if st.button('View game',key=f'pub_detail_{game["appid"]}'):
            st.session_state.selected_appid=game['appid']
            st.rerun()
