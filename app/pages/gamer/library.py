import pandas as pd
import streamlit as st
from app import auth, ui
from app.services import catalog, gamer, publisher, admin
account = auth.require_role('gamer')
ui.page_header('My Library', 'Your games and playtime')
if not ui.detail():
    rows = [g for g in gamer.library() if g['ownership_status'] in ('owned','borrowed')]
    open_session = next((s for s in gamer.sessions() if s['end_time'] is None),None)
    ui.grid(ui.paginate(rows,'library'),'library',mode='library',open_session=open_session)
    ui.chart(rows,'name','playtime_forever','library_chart')
