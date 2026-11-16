import pandas as pd
import streamlit as st
from app import auth, ui
from app.services import catalog, gamer, publisher, admin
account = auth.require_role('gamer')
ui.page_header('Store', 'Find your next game')
if not ui.detail():
    ui.store()
