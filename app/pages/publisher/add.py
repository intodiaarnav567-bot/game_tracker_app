import pandas as pd
import streamlit as st
from app import auth, ui
from app.services import catalog, gamer, publisher, admin
account = auth.require_role('game_publisher')
ui.page_header('Add Game', 'Publish a new game')
ui.game_form()
