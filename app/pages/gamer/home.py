import pandas as pd
import streamlit as st
from app import auth, ui
from app.services import catalog, gamer, publisher, admin
account = auth.require_role('gamer')
ui.page_header('Home', 'Your next session starts here')
if not ui.detail():
    library = gamer.library()
    games = [g for g in catalog.games() if g['is_active']]
    recent = sorted([g for g in library if g['ownership_status'] in ('owned','borrowed')],key=lambda g:str(g['last_played'] or ''),reverse=True)
    for title,rows in [('Continue playing',recent),('Top rated',sorted(games,key=lambda g:g['rating'],reverse=True)),('Free to play',[g for g in games if g['is_free']])]:
        st.subheader(title)
        if rows:
            ui.grid(rows[:4],title)
        else:
            ui.empty_state()
