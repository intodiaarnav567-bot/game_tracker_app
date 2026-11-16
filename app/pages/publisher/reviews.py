import pandas as pd
import streamlit as st
from app import auth, ui
from app.services import catalog, gamer, publisher, admin
account = auth.require_role('game_publisher')
ui.page_header('Reviews', 'Player feedback on your games')
games={g['appid']:g['name'] for g in publisher.games()}
if games:
    appid=st.selectbox('Game',games,format_func=games.get,key='pub_reviews_game')
    rows=publisher.reviews(appid)
    recommended = 100 * sum(r['recommended'] for r in rows) / len(rows) if rows else 0
    ui.metrics([('Recommended', f'{recommended:.0f}%')])
    search=st.text_input('Search reviews',key='pub_review_search')
    rows=[{k:r[k] for k in ('username','review_text','recommended','review_date')} for r in rows if search.lower() in (r['review_text'] or '').lower()]
    ui.table(rows,'pub_reviews')
else:
    ui.empty_state('Add a game first.')
