import pandas as pd
import streamlit as st
from app import auth, ui
from app.services import catalog, gamer, publisher, admin
account = auth.require_role('admin')
ui.page_header('Reviews', 'Manage player reviews')
search=st.text_input('Search reviews',key='admin_reviews_search')
rows=[r for r in catalog.reviews() if search.lower() in (r['review_text'] or '').lower()]
ui.table(rows,'admin_reviews')
options={r['review_id']:f"{r['username']} · {r['review_text'][:60]}" for r in rows}
if options:
    identifier=st.selectbox('Review',options,format_func=options.get,key='admin_review_select')
    if st.button('Delete review',key='admin_review_delete'):
        ui.confirm_dialog('Delete this review and its votes?',admin.delete_review,identifier)
