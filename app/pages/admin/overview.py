import pandas as pd
import streamlit as st
from app import auth, ui
from app.services import catalog, gamer, publisher, admin
account = auth.require_role('admin')
ui.page_header('Overview', 'Your collection platform at a glance')
view = st.segmented_control('View', ['Dashboard', 'Store'], default='Dashboard', key='dashboard_view')
if ui.detail():
    st.stop()
if view == 'Store':
    ui.store()
    st.stop()
metrics = [(label.replace('_', ' ').title(), value) for label, value in admin.overview().items()]
rows=admin.purchases()
if rows:
    frame=pd.DataFrame(rows)
    frame['price_paid']=pd.to_numeric(frame['price_paid'])
    for currency,group in frame.groupby('currency'):
        metrics.append((f'Revenue · {currency}', ui.fmt_money(group.price_paid.sum(), currency)))
ui.metrics(metrics)
if rows:
    frame['month']=frame.purchased_at.apply(lambda x:x.strftime('%Y-%m'))
    grouped=frame.groupby(['month','currency'],as_index=False).price_paid.sum()
    import plotly.express as px
    st.plotly_chart(px.bar(grouped,x='month',y='price_paid',color='currency',barmode='group'),key='admin_revenue')
ui.chart(admin.stats()[:10],'name','owners','admin_owners')
