import pandas as pd
import streamlit as st
from app import auth, ui
from app.services import catalog, gamer, publisher, admin
account = auth.require_role('game_publisher')
ui.page_header('Dashboard', 'Your games at a glance')
view = st.segmented_control('View', ['Dashboard', 'Store'], default='Dashboard', key='dashboard_view')
if ui.detail():
    st.stop()
if view == 'Store':
    ui.store()
    st.stop()
rows = publisher.stats()
owners=sum(r['owners'] for r in rows)
reviews=sum(r['review_count'] for r in rows)
metrics={'Games':len(rows),'Owners':owners,'Wishlists':sum(r['wishlists'] for r in rows),'Average playtime':ui.fmt_playtime(sum(r['avg_playtime_minutes']*r['owners'] for r in rows)/owners if owners else 0),'Reviews':reviews,'Recommended':f"{100*sum(r['recommended_count'] for r in rows)/reviews if reviews else 0:.0f}%"}
ui.metrics(metrics.items())
ui.chart(rows,'name','owners','publisher_owners')
