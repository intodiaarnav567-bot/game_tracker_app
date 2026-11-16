import pandas as pd
import streamlit as st
from app import auth, ui
from app.services import catalog, gamer, publisher, admin
account = auth.require_role('admin')
ui.page_header('Purchases', 'Purchase history and totals')
rows=admin.purchases()
user=st.text_input('User',key='purchase_user')
game=st.text_input('Game',key='purchase_game')
start=st.date_input('From',value=None,key='purchase_start')
end=st.date_input('To',value=None,key='purchase_end')
if start and end and end<start:
    st.error('The end date must be after the start date.')
else:
    rows=[r for r in rows if user.lower() in r['username'].lower() and game.lower() in r['name'].lower() and (not start or r['purchased_at'].date()>=start) and (not end or r['purchased_at'].date()<=end)]
    ui.table(rows,'purchases')
    if rows:
        frame=pd.DataFrame(rows)
        ui.metrics((currency, ui.fmt_money(group.price_paid.sum(), currency))
                   for currency, group in frame.groupby('currency'))
        st.download_button('Download CSV',frame.to_csv(index=False).encode(),'purchases.csv','text/csv',key='purchase_download')
