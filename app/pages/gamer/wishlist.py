import pandas as pd
import streamlit as st
from app import auth, ui
from app.services import catalog, gamer, publisher, admin
account = auth.require_role('gamer')
ui.page_header('Wishlist', 'Games you want to play')
if not ui.detail():
    rows = [g for g in gamer.library() if g['ownership_status']=='wishlist']
    ui.grid(ui.paginate(rows,'wishlist'),'wishlist',mode='wishlist')
